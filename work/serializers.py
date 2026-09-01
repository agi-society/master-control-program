from rest_framework import serializers
from .models import Person,Goal,Work,Dependency,Activity


class PersonSerializer(serializers.ModelSerializer):
    class Meta: model=Person; fields='__all__'


class GoalSerializer(serializers.ModelSerializer):
    class Meta: model=Goal; fields='__all__'


class WorkSerializer(serializers.ModelSerializer):
    owner_name=serializers.CharField(source='owner.name',read_only=True)
    created_by=serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model=Work
        fields='__all__'

    def validate(self,attrs):
        request=self.context.get('request')
        try: actor=request.user.person if request else None
        except Person.DoesNotExist: actor=None
        instance=self.instance
        if instance and instance.created_by_id and actor and instance.created_by_id != actor.id:
            if 'visibility' in attrs and attrs['visibility'] != instance.visibility:
                raise serializers.ValidationError({'visibility':'Only the creator can change visibility.'})
            if 'visible_to' in attrs:
                raise serializers.ValidationError({'visible_to':'Only the creator can change who private work is shared with.'})
            if instance.visibility=='private' and 'owner' in attrs and attrs['owner'] != instance.created_by:
                raise serializers.ValidationError({'owner':'Private work remains owned by its creator.'})
        parent=attrs.get('parent')
        if parent and request and not Work.objects.visible_to(request.user).filter(pk=parent.pk).exists():
            raise serializers.ValidationError({'parent':'That parent work item is not available to this user.'})
        return attrs

    def to_representation(self,instance):
        data=super().to_representation(instance)
        request=self.context.get('request')
        if instance.parent_id and request and not Work.objects.visible_to(request.user).filter(pk=instance.parent_id).exists():
            data['parent']=None
        return data


class DependencySerializer(serializers.ModelSerializer):
    class Meta: model=Dependency; fields='__all__'

    def validate(self,attrs):
        request=self.context.get('request')
        if request:
            allowed=Work.objects.visible_to(request.user)
            for field in ('work','depends_on'):
                obj=attrs.get(field,getattr(self.instance,field,None) if self.instance else None)
                if obj and not allowed.filter(pk=obj.pk).exists():
                    raise serializers.ValidationError({field:'That work item is not available to this user.'})
        return attrs


class ActivitySerializer(serializers.ModelSerializer):
    class Meta: model=Activity; fields='__all__'
