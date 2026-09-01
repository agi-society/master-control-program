from django.contrib import admin
from .models import Person,Goal,Work,Unit,Role

class RoleInline(admin.TabularInline):
    model=Role
    extra=0

@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display=('name','email','user','active','external_source')
    search_fields=('name','email')
    inlines=(RoleInline,)

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display=('name','type','parent','active','sort_order')
    list_filter=('type','active')
    search_fields=('name','description')
    inlines=(RoleInline,)

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display=('person','title','unit','is_lead','is_key_personnel','sort_order')
    list_filter=('unit','is_lead','is_key_personnel')
    search_fields=('person__name','title','unit__name')

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display=('title','status')

@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display=('title','type','unit','owner','status','visibility','created_by','color','board_order','planned_start','due_date','parent')
    list_filter=('type','status','risk','visibility','goal','unit')
    search_fields=('title','description','outcome')
    filter_horizontal=('collaborators','visible_to')
    readonly_fields=('created_by',)
    def get_queryset(self,request):
        return super().get_queryset(request).visible_to(request.user)
    def formfield_for_foreignkey(self,db_field,request,**kwargs):
        if db_field.name=='parent': kwargs['queryset']=Work.objects.visible_to(request.user)
        return super().formfield_for_foreignkey(db_field,request,**kwargs)
