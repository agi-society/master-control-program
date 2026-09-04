from django import forms
from .models import Work, Dependency

COLOR_CHOICES=[
    ('','Inherit / neutral'),
    ('#7C5CBF','Violet'),
    ('#5E8F62','Green'),
    ('#5279B8','Blue'),
    ('#B88731','Amber'),
    ('#B85C67','Rose'),
    ('#4F8B87','Teal'),
    ('#6B7280','Slate'),
]


class WorkForm(forms.ModelForm):
    dependencies=forms.ModelMultipleChoiceField(queryset=Work.objects.none(),required=False,help_text='Work that must happen before this can proceed.')
    color=forms.ChoiceField(choices=COLOR_CHOICES,required=False,help_text='Children inherit the parent color when left neutral.')
    class Meta:
        model=Work
        fields=['title','outcome','owner','goal','unit','type','color','planned_start','due_date','sunset_date','status','risk','visibility','visible_to','parent','exit_condition','description','collaborators']
        widgets={
            'planned_start':forms.DateInput(attrs={'type':'date'}),
            'due_date':forms.DateInput(attrs={'type':'date'}),
            'sunset_date':forms.DateInput(attrs={'type':'date'}),
            'collaborators':forms.CheckboxSelectMultiple(),
            'visible_to':forms.CheckboxSelectMultiple(),
        }
        labels={'visible_to':'Share private work with'}
        help_texts={'visible_to':'Only the creator and explicitly selected people can see private work.'}

    def __init__(self, *args, actor=None, **kwargs):
        self.actor = actor
        super().__init__(*args, **kwargs)

        user = getattr(actor, 'user', None) if actor else None
        qs = Work.objects.visible_to(user).order_by('title') if user else Work.objects.none()

        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
            self.fields['dependencies'].initial = list(
                self.instance.dependencies
                .filter(depends_on__in=qs)
                .values_list('depends_on_id', flat=True)
            )
        else:
            self.fields['dependencies'].initial = []

        self.fields['dependencies'].queryset = qs
        self.fields['parent'].queryset = qs
        self.fields['visible_to'].queryset = (
            self.fields['visible_to'].queryset
            .filter(active=True)
            .exclude(pk=getattr(actor, 'pk', None))
            .order_by('name')
        )

        # Sharing is creator-controlled. A person a private item is shared with may
        # work on it, but cannot re-share it, make it public, or reassign ownership.
        if (
            self.instance
            and self.instance.pk
            and self.instance.created_by_id
            and actor
            and self.instance.created_by_id != actor.id
        ):
            self.fields.pop('visibility', None)
            self.fields.pop('visible_to', None)

            if self.instance.visibility == 'private':
                self.fields.pop('owner', None)

            if self.instance.parent_id and not qs.filter(pk=self.instance.parent_id).exists():
                self.fields.pop('parent', None)

def clean(self):
        cleaned=super().clean()
        visibility=cleaned.get('visibility',getattr(self.instance,'visibility','org'))
        creator=getattr(self.instance,'created_by',None) or self.actor
        if visibility=='private' and creator:
            # Private work is personal work: sharing grants access, not ownership.
            cleaned['owner']=creator
        return cleaned

def save(self,commit=True):
        obj=super().save(commit=commit)
        if commit:
            if obj.visibility=='private' and obj.created_by_id:
                if obj.owner_id != obj.created_by_id:
                    obj.owner=obj.created_by
                    obj.save(update_fields=['owner','updated_at'])
            elif obj.visibility=='org':
                obj.visible_to.clear()
            Dependency.objects.filter(work=obj).delete()
            Dependency.objects.bulk_create([Dependency(work=obj,depends_on=d) for d in self.cleaned_data.get('dependencies',[])])
        return obj
