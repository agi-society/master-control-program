import csv
import json
from datetime import date
from django import forms
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Work,Person,Goal,Dependency,Activity,Unit,Role
from .forms import WorkForm


def _person(user):
    try: return user.person
    except Person.DoesNotExist: return None


def setup_admin(request):
    if User.objects.exists():
        return redirect('login')
    class SetupForm(UserCreationForm):
        email = forms.EmailField(required=False)
    if request.method=='POST':
        form=SetupForm(request.POST)
        if form.is_valid():
            user=form.save(commit=False); user.is_staff=True; user.is_superuser=True; user.email=form.cleaned_data['email']; user.save()
            Person.objects.create(user=user,name=user.username,email=user.email)
            login(request,user)
            return redirect('dashboard')
    else: form=SetupForm()
    return render(request,'work/setup.html',{'form':form})


def require_initialized(view):
    def inner(request,*a,**kw):
        if not User.objects.exists(): return redirect('setup_admin')
        return view(request,*a,**kw)
    return inner


def _work_matches_filter(work, assignee, due_by, viewer=None):
    if assignee == 'all':
        assignee_match=True
    elif assignee == 'unowned':
        assignee_match=work.owner_id is None
    else:
        try:
            assignee_id=int(assignee)
        except (TypeError,ValueError):
            assignee_match=False
        else:
            assignee_match=(work.owner_id==assignee_id or any(p.id==assignee_id for p in work.collaborators.all()))
            # "My Work" also includes private work explicitly shared with the
            # logged-in person, even though the creator remains its owner.
            if viewer and assignee_id==viewer.id and work.visibility=='private':
                assignee_match = assignee_match or work.visible_to.filter(pk=viewer.id).exists()
    if not assignee_match:
        return False
    if due_by:
        return bool(work.due_date and work.due_date <= due_by)
    return True


@require_initialized
@login_required
def dashboard(request):
    person=_person(request.user)
    default_assignee=str(person.id) if person else 'all'
    assignee=request.GET.get('assignee',default_assignee)
    due_by_raw=request.GET.get('due_by','').strip()
    try:
        due_by=date.fromisoformat(due_by_raw) if due_by_raw else None
    except ValueError:
        due_by=None
        due_by_raw=''

    visible_items=list(
        Work.objects.visible_to(request.user).exclude(status='cancelled')
        .select_related('owner','goal','parent','created_by')
        .prefetch_related('collaborators','visible_to')
    )
    visible_ids={w.id for w in visible_items}
    children_by_parent={}
    roots=[]
    for item in visible_items:
        if item.parent_id and item.parent_id in visible_ids:
            children_by_parent.setdefault(item.parent_id,[]).append(item)
        else:
            # If a shared private item has a parent the viewer cannot see, the
            # item becomes a visual root. The hidden parent leaves no UI trace.
            roots.append(item)
    map_rows=[]
    for root in roots:
        root_match=_work_matches_filter(root,assignee,due_by,person)
        children=[c for c in children_by_parent.get(root.id,[]) if _work_matches_filter(c,assignee,due_by,person)]
        if root_match or children:
            map_rows.append({'work':root,'children':children,'context_only':not root_match})

    people=Person.objects.filter(active=True).order_by('name')
    selected_label='All assignees'
    if assignee=='unowned': selected_label='Unowned'
    elif assignee not in ('all','unowned'):
        try: selected_label=people.get(pk=int(assignee)).name
        except (Person.DoesNotExist,ValueError,TypeError): selected_label='Assignee'
    return render(request,'work/dashboard.html',{
        'map_rows':map_rows,'people':people,'selected_assignee':assignee,
        'selected_label':selected_label,'due_by_raw':due_by_raw,'today':date.today(),
    })



@require_initialized
@login_required
def organization(request):
    units=list(Unit.objects.filter(active=True).select_related('parent').prefetch_related('roles__person').order_by('sort_order','name'))
    roots=[]
    children={}
    for unit in units:
        if unit.parent_id and any(u.id==unit.parent_id for u in units):
            children.setdefault(unit.parent_id,[]).append(unit)
        else:
            roots.append(unit)
    key_roles=Role.objects.filter(is_key_personnel=True,unit__active=True,person__active=True).select_related('person','unit').order_by('sort_order','person__name')
    return render(request,'work/organization.html',{'roots':roots,'children':children,'key_roles':key_roles})


@require_initialized
@login_required
def person_detail(request,pk):
    person=get_object_or_404(Person.objects.prefetch_related('roles__unit'),pk=pk,active=True)
    roles=person.roles.filter(unit__active=True).select_related('unit').order_by('unit__sort_order','sort_order','unit__name')
    work=Work.objects.visible_to(request.user).filter(owner=person).select_related('unit').order_by('status','due_date','title')[:50]
    return render(request,'work/person_detail.html',{'person':person,'roles':roles,'person_work':work})


@require_initialized
@login_required
def board(request):
    visible=Work.objects.visible_to(request.user)
    groups={k:visible.filter(status=k).exclude(status='cancelled').select_related('owner','parent','created_by').prefetch_related('visible_to').order_by('board_order','due_date','title') for k,_ in Work.STATUSES if k!='cancelled'}
    return render(request,'work/board.html',{'groups':groups,'status_labels':dict(Work.STATUSES)})


@require_initialized
@login_required
@require_POST
def board_reorder(request):
    try:
        payload=json.loads(request.body.decode('utf-8'))
        columns=payload['columns']
        dragged_id=int(payload['work_id'])
    except (ValueError,TypeError,KeyError,json.JSONDecodeError):
        return JsonResponse({'ok':False,'error':'Invalid board update.'},status=400)

    valid_statuses=[k for k,_ in Work.STATUSES if k!='cancelled']
    if not isinstance(columns,dict) or any(k not in valid_statuses for k in columns):
        return JsonResponse({'ok':False,'error':'Invalid status column.'},status=400)

    ids=[]
    for status in valid_statuses:
        col=columns.get(status,[])
        if not isinstance(col,list):
            return JsonResponse({'ok':False,'error':'Invalid ordering.'},status=400)
        try: ids.extend(int(x) for x in col)
        except (TypeError,ValueError): return JsonResponse({'ok':False,'error':'Invalid work id.'},status=400)
    if len(ids)!=len(set(ids)):
        return JsonResponse({'ok':False,'error':'A work item appears more than once.'},status=400)

    existing={w.id:w for w in Work.objects.visible_to(request.user).filter(id__in=ids)}
    if set(existing)!=set(ids) or dragged_id not in existing:
        return JsonResponse({'ok':False,'error':'Unknown work item.'},status=404)

    actor=_person(request.user)
    with transaction.atomic():
        for status in valid_statuses:
            for order,work_id in enumerate(columns.get(status,[])):
                work=existing[int(work_id)]
                old_status=work.status
                changed=(work.status!=status or work.board_order!=order)
                if not changed: continue
                work.status=status
                work.board_order=order
                if status=='done' and old_status!='done': work.completed_at=timezone.now()
                elif status!='done' and old_status=='done': work.completed_at=None
                work.save(update_fields=['status','board_order','completed_at','updated_at'])
                if old_status!=status:
                    Activity.objects.create(work=work,actor=actor,event_type='status.changed',data={'from':old_status,'to':status,'source':'board_drag'})
        Activity.objects.create(work=existing[dragged_id],actor=actor,event_type='board.reordered')
    return JsonResponse({'ok':True})


@require_initialized
@login_required
def my_work_legacy(request):
    return redirect('dashboard')


@require_initialized
@login_required
def work_create(request):
    actor=_person(request.user)
    if not actor:
        return HttpResponse('This account needs a linked Person profile before creating work.',status=400)
    initial={}
    if request.method!='POST' and request.GET.get('parent'):
        parent=Work.objects.visible_to(request.user).filter(pk=request.GET.get('parent')).first()
        if parent: initial['parent']=parent.pk
    form=WorkForm(request.POST or None, initial=initial, actor=actor)
    if request.method=='POST' and form.is_valid():
        form.instance.created_by=actor
        w=form.save()
        max_order=(Work.objects.filter(status=w.status).exclude(pk=w.pk).aggregate(m=Max('board_order'))['m'] or 0)
        if Work.objects.filter(status=w.status).exclude(pk=w.pk).exists():
            w.board_order=max_order+1; w.save(update_fields=['board_order','updated_at'])
        Activity.objects.create(work=w,actor=actor,event_type='work.created',data={'visibility':w.visibility})
        return redirect('work_detail',pk=w.pk)
    return render(request,'work/work_form.html',{'form':form,'heading':'Create work'})


@require_initialized
@login_required
def work_edit(request,pk):
    actor=_person(request.user)
    w=get_object_or_404(Work.objects.visible_to(request.user),pk=pk)
    old_color=w.color
    old_visibility=w.visibility
    form=WorkForm(request.POST or None,instance=w,actor=actor)
    if request.method=='POST' and form.is_valid():
        # Legacy seeded/org work predates creator tracking. The first person who
        # edits such an item establishes its creator for future privacy changes.
        if w.created_by_id is None and actor:
            form.instance.created_by=actor
        w=form.save(); Activity.objects.create(work=w,actor=actor,event_type='work.updated')
        if old_color!=w.color:
            Activity.objects.create(work=w,actor=actor,event_type='color.changed',data={'from':old_color,'to':w.color})
        if old_visibility!=w.visibility:
            Activity.objects.create(work=w,actor=actor,event_type='visibility.changed',data={'from':old_visibility,'to':w.visibility})
        return redirect('work_detail',pk=w.pk)
    return render(request,'work/work_form.html',{'form':form,'heading':f'Edit {w.title}'})


@require_initialized
@login_required
def work_detail(request,pk):
    visible=Work.objects.visible_to(request.user)
    w=get_object_or_404(visible.select_related('owner','goal','parent','created_by').prefetch_related('collaborators','visible_to','activity'),pk=pk)
    visible_ids=visible.values_list('id',flat=True)
    children=visible.filter(parent=w).select_related('owner','parent','created_by')
    dependencies=Dependency.objects.filter(work=w,depends_on_id__in=visible_ids).select_related('depends_on','depends_on__owner')
    return render(request,'work/work_detail.html',{'w':w,'visible_children':children,'visible_dependencies':dependencies})


@require_initialized
@login_required
@require_POST
def work_status(request,pk):
    w=get_object_or_404(Work.objects.visible_to(request.user),pk=pk); old=w.status; new=request.POST.get('status')
    if new in dict(Work.STATUSES):
        w.status=new
        if new=='done': w.completed_at=timezone.now()
        elif old=='done': w.completed_at=None
        w.save(update_fields=['status','completed_at','updated_at'])
        Activity.objects.create(work=w,actor=_person(request.user),event_type='status.changed',data={'from':old,'to':new})
    return redirect(request.POST.get('next') or 'work_detail',pk=w.pk)


@require_initialized
@login_required
def export_work_csv(request):
    visible=Work.objects.visible_to(request.user).select_related('owner','goal','parent','created_by').prefetch_related('visible_to')
    visible_ids=set(visible.values_list('id',flat=True))
    r=HttpResponse(content_type='text/csv'); r['Content-Disposition']='attachment; filename="agis-work.csv"'
    w=csv.writer(r); w.writerow(['id','title','type','status','visibility','created_by','shared_with','owner','goal','parent','planned_start','due_date','color','board_order','outcome','exit_condition'])
    for x in visible:
        parent_title=x.parent.title if x.parent_id in visible_ids else ''
        shared=', '.join(p.name for p in x.visible_to.all()) if x.visibility=='private' else ''
        w.writerow([x.id,x.title,x.type,x.status,x.visibility,x.created_by.name if x.created_by else '',shared,x.owner.name if x.owner else '',x.goal.title if x.goal else '',parent_title,x.planned_start or '',x.due_date or '',x.color,x.board_order,x.outcome,x.exit_condition])
    return r


@require_initialized
@login_required
def export_snapshot_json(request):
    visible=list(Work.objects.visible_to(request.user).select_related('owner','goal','parent','created_by').prefetch_related('visible_to','collaborators'))
    visible_ids={w.id for w in visible}
    work=[]
    for item in visible:
        work.append({
            'id':item.id,'title':item.title,'type':item.type,'status':item.status,'risk':item.risk,
            'visibility':item.visibility,'created_by_id':item.created_by_id,
            'visible_to_ids':[p.id for p in item.visible_to.all()] if item.visibility=='private' else [],
            'owner_id':item.owner_id,'goal_id':item.goal_id,
            'parent_id':item.parent_id if item.parent_id in visible_ids else None,
            'collaborator_ids':[p.id for p in item.collaborators.all()],
            'planned_start':item.planned_start,'due_date':item.due_date,'sunset_date':item.sunset_date,
            'outcome':item.outcome,'exit_condition':item.exit_condition,'description':item.description,
            'color':item.color,'board_order':item.board_order,'completed_at':item.completed_at,
            'external_source':item.external_source,'external_id':item.external_id,
            'created_at':item.created_at,'updated_at':item.updated_at,
        })
    dependencies=list(Dependency.objects.filter(work_id__in=visible_ids,depends_on_id__in=visible_ids).values())
    activity=list(Activity.objects.filter(work_id__in=visible_ids).values())
    data={'people':list(Person.objects.values()),'goals':list(Goal.objects.values()),'work':work,'dependencies':dependencies,'activity':activity}
    return JsonResponse(data)
