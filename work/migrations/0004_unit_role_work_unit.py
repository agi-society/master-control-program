from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[('work','0003_work_visibility')]
    operations=[
        migrations.CreateModel(name='Unit',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('name',models.CharField(max_length=160)),('type',models.CharField(choices=[('leadership','Leadership'),('chapter','Chapter'),('conference','Conference'),('journal','Journal'),('reports','Reports'),('education','Education'),('program','Program'),('other','Other')],default='other',max_length=20)),('description',models.TextField(blank=True)),('sort_order',models.PositiveIntegerField(default=0)),('active',models.BooleanField(default=True)),('parent',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name='children',to='work.unit'))],options={'ordering':['sort_order','name']}),
        migrations.CreateModel(name='Role',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('title',models.CharField(max_length=120)),('is_lead',models.BooleanField(default=False)),('is_key_personnel',models.BooleanField(default=False)),('sort_order',models.PositiveIntegerField(default=0)),('person',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='roles',to='work.person')),('unit',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='roles',to='work.unit'))],options={'ordering':['sort_order','person__name','title']}),
        migrations.AddConstraint(model_name='role',constraint=models.UniqueConstraint(fields=('person','unit','title'),name='unique_person_unit_role')),
        migrations.AddField(model_name='work',name='unit',field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name='work_items',to='work.unit')),
    ]
