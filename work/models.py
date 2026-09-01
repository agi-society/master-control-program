from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Person(models.Model):
    user=models.OneToOneField(User,on_delete=models.SET_NULL,null=True,blank=True,related_name='person')
    name=models.CharField(max_length=120)
    email=models.EmailField(blank=True)
    active=models.BooleanField(default=True)
    external_source=models.CharField(max_length=40,blank=True)
    external_id=models.CharField(max_length=120,blank=True)
    notes=models.TextField(blank=True)
    def __str__(self): return self.name


class Unit(models.Model):
    TYPES=[('leadership','Leadership'),('chapter','Chapter'),('conference','Conference'),('journal','Journal'),('reports','Reports'),('education','Education'),('program','Program'),('other','Other')]
    name=models.CharField(max_length=160)
    type=models.CharField(max_length=20,choices=TYPES,default='other')
    parent=models.ForeignKey('self',on_delete=models.SET_NULL,null=True,blank=True,related_name='children')
    description=models.TextField(blank=True)
    sort_order=models.PositiveIntegerField(default=0)
    active=models.BooleanField(default=True)
    class Meta:
        ordering=['sort_order','name']
    def __str__(self): return self.name


class Role(models.Model):
    person=models.ForeignKey(Person,on_delete=models.CASCADE,related_name='roles')
    unit=models.ForeignKey(Unit,on_delete=models.CASCADE,related_name='roles')
    title=models.CharField(max_length=120)
    is_lead=models.BooleanField(default=False)
    is_key_personnel=models.BooleanField(default=False)
    sort_order=models.PositiveIntegerField(default=0)
    class Meta:
        ordering=['sort_order','person__name','title']
        constraints=[models.UniqueConstraint(fields=['person','unit','title'],name='unique_person_unit_role')]
    def __str__(self): return f'{self.person} — {self.title} ({self.unit})'


class Goal(models.Model):
    title=models.CharField(max_length=200,unique=True)
    description=models.TextField(blank=True)
    status=models.CharField(max_length=20,default='active')
    def __str__(self): return self.title


class WorkQuerySet(models.QuerySet):
    def visible_to(self,user):
        """Work the authenticated user's Person may know exists.

        Organization work is visible to every authenticated user. Private work is
        visible only to its creator and people explicitly listed in visible_to.
        There is deliberately no superuser bypass here: normal app/API reads obey
        the same privacy rule for everyone.
        """
        if not user or not getattr(user,'is_authenticated',False):
            return self.none()
        try:
            person=user.person
        except Person.DoesNotExist:
            return self.filter(visibility='org')
        return self.filter(
            Q(visibility='org') |
            Q(visibility='private',created_by=person) |
            Q(visibility='private',visible_to=person)
        ).distinct()


class Work(models.Model):
    TYPES=[('project','Project'),('deliverable','Deliverable'),('task','Task')]
    STATUSES=[('proposed','Proposed'),('ready','Ready'),('in_progress','In Progress'),('blocked','Blocked'),('done','Done'),('cancelled','Cancelled')]
    RISKS=[('normal','Normal'),('at_risk','At Risk')]
    VISIBILITIES=[('org','Organization'),('private','Private')]
    parent=models.ForeignKey('self',on_delete=models.CASCADE,null=True,blank=True,related_name='children')
    goal=models.ForeignKey(Goal,on_delete=models.SET_NULL,null=True,blank=True,related_name='work_items')
    unit=models.ForeignKey(Unit,on_delete=models.SET_NULL,null=True,blank=True,related_name='work_items')
    type=models.CharField(max_length=20,choices=TYPES,default='task')
    title=models.CharField(max_length=240)
    description=models.TextField(blank=True)
    owner=models.ForeignKey(Person,on_delete=models.SET_NULL,null=True,blank=True,related_name='owned_work')
    collaborators=models.ManyToManyField(Person,blank=True,related_name='collaborations')
    planned_start=models.DateField(null=True,blank=True)
    due_date=models.DateField(null=True,blank=True)
    sunset_date=models.DateField(null=True,blank=True)
    outcome=models.TextField(blank=True)
    exit_condition=models.TextField(blank=True)
    status=models.CharField(max_length=20,choices=STATUSES,default='proposed')
    risk=models.CharField(max_length=20,choices=RISKS,default='normal')
    visibility=models.CharField(max_length=16,choices=VISIBILITIES,default='org',db_index=True)
    created_by=models.ForeignKey(Person,on_delete=models.PROTECT,null=True,blank=True,related_name='created_work')
    visible_to=models.ManyToManyField(Person,blank=True,related_name='shared_private_work')
    color=models.CharField(max_length=7,blank=True,default='',help_text='Hex color, e.g. #6B5DD3')
    board_order=models.PositiveIntegerField(default=0,db_index=True)
    completed_at=models.DateTimeField(null=True,blank=True)
    external_source=models.CharField(max_length=40,blank=True)
    external_id=models.CharField(max_length=120,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    objects=WorkQuerySet.as_manager()
    class Meta:
        ordering=['board_order','due_date','title']
    def clean(self):
        if self.planned_start and self.due_date and self.planned_start > self.due_date:
            raise ValidationError({'due_date':'Due date must be on or after planned start.'})
        if self.parent_id and self.parent_id == self.id:
            raise ValidationError({'parent':'Work cannot be its own parent.'})
        if self.visibility=='private' and self.created_by_id and self.owner_id and self.owner_id != self.created_by_id:
            raise ValidationError({'owner':'Private work remains owned by its creator. Share access instead of assigning it.'})
    @property
    def display_color(self):
        if self.color:
            return self.color
        if self.parent_id and self.parent and self.parent.color:
            return self.parent.color
        return '#6B7280'
    def __str__(self): return self.title


class Dependency(models.Model):
    work=models.ForeignKey(Work,on_delete=models.CASCADE,related_name='dependencies')
    depends_on=models.ForeignKey(Work,on_delete=models.CASCADE,related_name='dependents')
    class Meta:
        constraints=[models.UniqueConstraint(fields=['work','depends_on'],name='unique_dependency')]
    def clean(self):
        if self.work_id and self.work_id == self.depends_on_id:
            raise ValidationError('Work cannot depend on itself.')
    def __str__(self): return f'{self.work} depends on {self.depends_on}'


class Comment(models.Model):
    work=models.ForeignKey(Work,on_delete=models.CASCADE,related_name='comments')
    person=models.ForeignKey(Person,on_delete=models.SET_NULL,null=True,blank=True)
    body=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)


class Link(models.Model):
    work=models.ForeignKey(Work,on_delete=models.CASCADE,related_name='links')
    title=models.CharField(max_length=160)
    url=models.URLField()


class Activity(models.Model):
    work=models.ForeignKey(Work,on_delete=models.CASCADE,related_name='activity')
    actor=models.ForeignKey(Person,on_delete=models.SET_NULL,null=True,blank=True)
    event_type=models.CharField(max_length=80)
    data=models.JSONField(default=dict,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['-created_at']
