from datetime import date
from django.core.management.base import BaseCommand
from work.models import Goal,Work

class Command(BaseCommand):
    help='Idempotently seed AGI Society work supplied for the MVP.'
    def handle(self,*args,**kwargs):
        goals={}
        for title in ['Governance & Board','Website & Communications','Global Chapters','AGI-27 Conference','Publications & Assessments','Operations & Funding']:
            goals[title],_=Goal.objects.get_or_create(title=title)
        def upsert(title,**fields):
            obj,created=Work.objects.get_or_create(title=title,defaults=fields)
            if not created and fields.get('color') and not obj.color:
                obj.color=fields['color']; obj.save(update_fields=['color','updated_at'])
            if created: self.stdout.write(f'created: {title}')
            return obj
        board=upsert('Board Appointments',type='project',color='#6B7280',goal=goals['Governance & Board'],status='ready',outcome='Board roles and appointments resolved.')
        upsert('Send separate asks to each board member for introductions',type='deliverable',parent=board,goal=goals['Governance & Board'],status='ready',planned_start=date(2026,8,17),outcome='Each board member receives a tailored introduction ask.')
        web=upsert('New AGI Society website',type='project',color='#B88731',goal=goals['Website & Communications'],status='ready',planned_start=date(2026,8,17),outcome='New AGI Society website live, tested, and ready to support chapter/event communications.')
        for t in ['Build website','Hosting / DNS','Test website','Launch website']:
            upsert(t,type='task',parent=web,goal=goals['Website & Communications'],status='ready',planned_start=date(2026,8,17))
        social=upsert('Social Media Set Up',type='project',color='#B85C67',goal=goals['Website & Communications'],status='ready',planned_start=date(2026,8,17),outcome='Core Society social accounts configured and visually aligned with the website.')
        for t in ['Set up social media accounts','Apply website-aligned branding','Publish initial social media posts']:
            upsert(t,type='task',parent=social,goal=goals['Website & Communications'],status='ready',planned_start=date(2026,8,17))
        upsert('Press release posted on Social Media',type='deliverable',color='#B85C67',goal=goals['Website & Communications'],status='ready')
        boston=upsert('Boston Chapter Launch',type='project',color='#5279B8',goal=goals['Global Chapters'],status='in_progress',due_date=date(2026,8,27),outcome='Successful public Boston chapter launch event.')
        sf=upsert('SF Chapter Launch',type='project',color='#5279B8',goal=goals['Global Chapters'],status='proposed',outcome='San Francisco chapter launch date and initial event plan established.')
        sea=upsert('Seattle Chapter Launch',type='project',color='#5279B8',goal=goals['Global Chapters'],status='proposed',outcome='Seattle chapter launch date and initial event plan established.')
        upsert('Put dates down for SF and Seattle chapter launches',type='deliverable',color='#5279B8',goal=goals['Global Chapters'],status='ready',planned_start=date(2026,8,17),outcome='SF and Seattle have explicit target launch dates.')
        upsert('Dubai Chapter Launch',type='project',color='#4F8B87',goal=goals['Global Chapters'],status='in_progress',due_date=date(2026,9,8),outcome='Dubai chapter launch completed.')
        upsert('Mauritius Event',type='project',color='#4F8B87',goal=goals['Global Chapters'],status='in_progress',due_date=date(2026,9,11),outcome='Mauritius forum/fundraising event completed.')
        conf=upsert('Initial Conference Discussions',type='project',color='#5E8F62',goal=goals['AGI-27 Conference'],status='in_progress',outcome='Initial AGI-27 direction converted into an actionable conference plan.')
        upsert('Draft conference plan',type='deliverable',parent=conf,goal=goals['AGI-27 Conference'],status='ready',planned_start=date(2026,8,17),outcome='A reviewable first draft of the AGI-27 conference plan exists.')
        upsert('State of AGI report timeline done',type='deliverable',color='#7C5CBF',goal=goals['Publications & Assessments'],status='done',outcome='State of AGI report timeline completed.')
        upsert('AI & Labor Report skeleton',type='deliverable',color='#7C5CBF',goal=goals['Publications & Assessments'],status='ready',planned_start=date(2026,8,17),outcome='A reviewable report skeleton with major sections and owners exists.')
        upsert('Deposit Money into Bank',type='task',color='#6B7280',goal=goals['Operations & Funding'],status='ready',outcome='Funds deposited into Society bank account.')
        self.stdout.write(self.style.SUCCESS('Seed complete. Existing matching titles are left untouched.'))
