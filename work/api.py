from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from .models import Person,Goal,Work,Dependency,Activity
from .serializers import PersonSerializer,GoalSerializer,WorkSerializer,DependencySerializer,ActivitySerializer


def _person(user):
    try: return user.person
    except Person.DoesNotExist: return None


class PersonViewSet(viewsets.ModelViewSet):
    queryset=Person.objects.all(); serializer_class=PersonSerializer


class GoalViewSet(viewsets.ModelViewSet):
    queryset=Goal.objects.all(); serializer_class=GoalSerializer


class WorkViewSet(viewsets.ModelViewSet):
    serializer_class=WorkSerializer
    def get_queryset(self):
        return Work.objects.visible_to(self.request.user).select_related('owner','goal','parent','created_by').prefetch_related('collaborators','visible_to')
    def perform_create(self,serializer):
        actor=_person(self.request.user)
        if not actor:
            raise PermissionDenied('A Person profile must be linked to this account before creating work.')
        visibility=serializer.validated_data.get('visibility','org')
        kwargs={'created_by':actor}
        if visibility=='private': kwargs['owner']=actor
        serializer.save(**kwargs)
    def perform_update(self,serializer):
        actor=_person(self.request.user)
        instance=self.get_object()
        new_visibility=serializer.validated_data.get('visibility',instance.visibility)
        kwargs={}
        if instance.created_by_id is None:
            kwargs['created_by']=actor
        creator=instance.created_by or actor
        if new_visibility=='private' and creator:
            kwargs['owner']=creator
        serializer.save(**kwargs)
        if serializer.instance.visibility=='org':
            serializer.instance.visible_to.clear()


class DependencyViewSet(viewsets.ModelViewSet):
    serializer_class=DependencySerializer
    def get_queryset(self):
        visible=Work.objects.visible_to(self.request.user)
        visible_ids=visible.values_list('id',flat=True)
        return Dependency.objects.filter(work_id__in=visible_ids,depends_on_id__in=visible_ids)


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=ActivitySerializer
    def get_queryset(self):
        visible_ids=Work.objects.visible_to(self.request.user).values_list('id',flat=True)
        return Activity.objects.filter(work_id__in=visible_ids)
