from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('work','0001_initial')]
    operations=[
        migrations.AddField(model_name='work',name='color',field=models.CharField(blank=True,default='',help_text='Hex color, e.g. #6B5DD3',max_length=7)),
        migrations.AddField(model_name='work',name='board_order',field=models.PositiveIntegerField(db_index=True,default=0)),
        migrations.AlterModelOptions(name='work',options={'ordering':['board_order','due_date','title']}),
    ]
