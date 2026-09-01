from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies=[('work','0002_work_color_board_order')]
    operations=[
        migrations.AddField(
            model_name='work',name='visibility',
            field=models.CharField(choices=[('org','Organization'),('private','Private')],db_index=True,default='org',max_length=16),
        ),
        migrations.AddField(
            model_name='work',name='created_by',
            field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name='created_work',to='work.person'),
        ),
        migrations.AddField(
            model_name='work',name='visible_to',
            field=models.ManyToManyField(blank=True,related_name='shared_private_work',to='work.person'),
        ),
    ]
