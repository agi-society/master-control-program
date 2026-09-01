from datetime import date
from django.test import TestCase,Client
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from .models import Work,Person,Goal,Dependency,Unit,Role

class WorkModelTests(TestCase):
    def test_due_date_cannot_precede_start(self):
        w=Work(title='x',planned_start=date(2026,8,20),due_date=date(2026,8,19))
        with self.assertRaises(ValidationError): w.full_clean()
    def test_work_cannot_depend_on_itself(self):
        w=Work.objects.create(title='x')
        d=Dependency(work=w,depends_on=w)
        with self.assertRaises(ValidationError): d.full_clean()

class SetupFlowTests(TestCase):
    def test_first_visit_redirects_to_setup(self):
        r=Client().get('/')
        self.assertRedirects(r,'/setup/')
    def test_setup_creates_superuser_and_person(self):
        r=Client().post('/setup/',{'username':'admin','email':'a@example.com','password1':'verystrongpass123','password2':'verystrongpass123'})
        self.assertEqual(r.status_code,302)
        u=User.objects.get(username='admin')
        self.assertTrue(u.is_superuser)
        self.assertEqual(u.person.email,'a@example.com')

class SeedTests(TestCase):
    def test_seed_is_idempotent_and_contains_user_supplied_work(self):
        call_command('seed_data'); first=Work.objects.count(); call_command('seed_data')
        self.assertEqual(first,Work.objects.count())
        for title in ['Board Appointments','New AGI Society website','Boston Chapter Launch','SF Chapter Launch','Dubai Chapter Launch','Mauritius Event','Initial Conference Discussions','State of AGI report timeline done','Press release posted on Social Media','Social Media Set Up','Deposit Money into Bank','Seattle Chapter Launch','AI & Labor Report skeleton']:
            self.assertTrue(Work.objects.filter(title=title).exists(),title)

class APITests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user('u',password='p')
        Person.objects.create(user=self.user,name='U')
        Work.objects.create(title='API task')
    def test_work_api_requires_auth(self):
        self.assertIn(Client().get('/api/work/').status_code,[401,403])
    def test_work_api_returns_items_when_logged_in(self):
        c=Client(); c.login(username='u',password='p')
        r=c.get('/api/work/')
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()[0]['title'],'API task')
    def test_csv_export(self):
        c=Client(); c.login(username='u',password='p')
        r=c.get('/api/export/work.csv')
        self.assertEqual(r.status_code,200)
        self.assertIn(b'API task',r.content)

class WorkColorTests(TestCase):
    def test_child_inherits_parent_color(self):
        parent=Work.objects.create(title='Parent',color='#5279B8')
        child=Work.objects.create(title='Child',parent=parent)
        self.assertEqual(child.display_color,'#5279B8')
    def test_child_can_override_parent_color(self):
        parent=Work.objects.create(title='Parent',color='#5279B8')
        child=Work.objects.create(title='Child',parent=parent,color='#B88731')
        self.assertEqual(child.display_color,'#B88731')

class MyWorkMapTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user('maya',password='p')
        self.maya=Person.objects.create(user=self.user,name='Maya')
        self.alex=Person.objects.create(name='Alex')
        self.mine=Work.objects.create(title='Mine',owner=self.maya,due_date=date(2026,8,25),color='#7C5CBF')
        self.other=Work.objects.create(title='Other',owner=self.alex,due_date=date(2026,8,20))
        self.later=Work.objects.create(title='Mine later',owner=self.maya,due_date=date(2026,9,20))
        self.client.login(username='maya',password='p')
    def test_default_map_filters_to_logged_in_person(self):
        r=self.client.get('/')
        self.assertContains(r,'Mine')
        self.assertContains(r,'Mine later')
        self.assertNotContains(r,'Other')
    def test_due_by_filter_limits_visible_work(self):
        r=self.client.get(f'/?assignee={self.maya.id}&due_by=2026-08-31')
        self.assertContains(r,'Mine')
        self.assertNotContains(r,'Mine later')
    def test_all_assignees_filter(self):
        r=self.client.get('/?assignee=all')
        self.assertContains(r,'Mine')
        self.assertContains(r,'Other')

class BoardDragTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user('u2',password='p')
        Person.objects.create(user=self.user,name='U2')
        self.a=Work.objects.create(title='A',status='ready',board_order=0)
        self.b=Work.objects.create(title='B',status='ready',board_order=1)
        self.c=Work.objects.create(title='C',status='in_progress',board_order=0)
        self.client.login(username='u2',password='p')
    def test_drag_can_change_status_and_order(self):
        import json
        payload={'work_id':self.b.id,'columns':{
            'proposed':[],
            'ready':[self.a.id],
            'in_progress':[self.b.id,self.c.id],
            'blocked':[],
            'done':[],
        }}
        r=self.client.post('/board/reorder/',data=json.dumps(payload),content_type='application/json')
        self.assertEqual(r.status_code,200)
        self.b.refresh_from_db(); self.c.refresh_from_db()
        self.assertEqual(self.b.status,'in_progress')
        self.assertEqual(self.b.board_order,0)
        self.assertEqual(self.c.board_order,1)
    def test_drag_reorders_within_column(self):
        import json
        payload={'work_id':self.b.id,'columns':{
            'proposed':[],
            'ready':[self.b.id,self.a.id],
            'in_progress':[self.c.id],
            'blocked':[],
            'done':[],
        }}
        r=self.client.post('/board/reorder/',data=json.dumps(payload),content_type='application/json')
        self.assertEqual(r.status_code,200)
        self.a.refresh_from_db(); self.b.refresh_from_db()
        self.assertEqual(self.b.board_order,0)
        self.assertEqual(self.a.board_order,1)

class StaticAssetTests(TestCase):
    def test_static_assets_are_discoverable(self):
        from django.contrib.staticfiles import finders
        self.assertTrue(finders.find('work/app.css'))
        self.assertTrue(finders.find('work/app.js'))

class PrivateWorkVisibilityTests(TestCase):
    def setUp(self):
        self.alice_user=User.objects.create_user('alice',password='p')
        self.alice=Person.objects.create(user=self.alice_user,name='Alice')
        self.s0_user=User.objects.create_user('s0',password='p')
        self.s0=Person.objects.create(user=self.s0_user,name='System Zero')
        self.bob_user=User.objects.create_user('bob',password='p')
        self.bob=Person.objects.create(user=self.bob_user,name='Bob')
        self.org=Work.objects.create(title='Org work',visibility='org',created_by=self.alice,owner=self.alice)
        self.private=Work.objects.create(title='Private thought',visibility='private',created_by=self.alice,owner=self.alice)
        self.private.visible_to.add(self.s0)

    def test_creator_and_explicit_share_can_see_private_work(self):
        self.assertTrue(Work.objects.visible_to(self.alice_user).filter(pk=self.private.pk).exists())
        self.assertTrue(Work.objects.visible_to(self.s0_user).filter(pk=self.private.pk).exists())

    def test_unshared_user_sees_no_private_work(self):
        self.assertFalse(Work.objects.visible_to(self.bob_user).filter(pk=self.private.pk).exists())
        c=Client(); c.login(username='bob',password='p')
        self.assertEqual(c.get(f'/work/{self.private.pk}/').status_code,404)
        self.assertNotContains(c.get('/board/'),'Private thought')
        self.assertNotContains(c.get('/?assignee=all'),'Private thought')

    def test_shared_private_work_appears_on_shared_users_default_my_work(self):
        c=Client(); c.login(username='s0',password='p')
        self.assertContains(c.get('/'),'Private thought')

    def test_api_and_exports_do_not_leak_private_work(self):
        c=Client(); c.login(username='bob',password='p')
        api=c.get('/api/work/').json()
        self.assertFalse(any(item['id']==self.private.id for item in api))
        self.assertNotIn(b'Private thought',c.get('/api/export/work.csv').content)
        snap=c.get('/api/export/snapshot.json').json()
        self.assertFalse(any(item['id']==self.private.id for item in snap['work']))

    def test_dependency_exists_only_when_both_ends_are_visible(self):
        public_target=Work.objects.create(title='Public target',visibility='org',created_by=self.alice,owner=self.alice)
        dep=Dependency.objects.create(work=public_target,depends_on=self.private)
        alice=Client(); alice.login(username='alice',password='p')
        bob=Client(); bob.login(username='bob',password='p')
        self.assertTrue(any(item['id']==dep.id for item in alice.get('/api/dependencies/').json()))
        self.assertFalse(any(item['id']==dep.id for item in bob.get('/api/dependencies/').json()))
        self.assertContains(alice.get(f'/work/{public_target.id}/'),'Private thought')
        self.assertNotContains(bob.get(f'/work/{public_target.id}/'),'Private thought')

    def test_board_reorder_cannot_mutate_invisible_private_work(self):
        import json
        c=Client(); c.login(username='bob',password='p')
        payload={'work_id':self.private.id,'columns':{
            'proposed':[self.org.id,self.private.id],
            'ready':[], 'in_progress':[], 'blocked':[], 'done':[],
        }}
        r=c.post('/board/reorder/',data=json.dumps(payload),content_type='application/json')
        self.assertEqual(r.status_code,404)
        self.private.refresh_from_db()
        self.assertEqual(self.private.status,'proposed')

    def test_private_owner_must_remain_creator(self):
        self.private.owner=self.s0
        with self.assertRaises(ValidationError):
            self.private.full_clean()


class OrganizationTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user('orguser',password='p')
        self.person=Person.objects.create(user=self.user,name='Conference Person')
        self.chapter=Unit.objects.create(name='Boston',type='chapter',sort_order=2)
        self.conference=Unit.objects.create(name='Conference',type='conference',sort_order=1)
        Role.objects.create(person=self.person,unit=self.conference,title='Co-Lead',is_lead=True,is_key_personnel=True)
        Role.objects.create(person=self.person,unit=self.chapter,title='Chapter Lead',is_lead=True)
        self.client.login(username='orguser',password='p')
    def test_person_can_hold_roles_in_multiple_units(self):
        self.assertEqual(self.person.roles.count(),2)
    def test_organization_page_shows_units_and_roles(self):
        r=self.client.get('/organization/')
        self.assertEqual(r.status_code,200)
        self.assertContains(r,'Conference')
        self.assertContains(r,'Boston')
        self.assertContains(r,'Co-Lead')
        self.assertContains(r,'Chapter Lead')
        self.assertContains(r,'Key personnel')
    def test_person_page_shows_multiple_roles(self):
        r=self.client.get(f'/people/{self.person.id}/')
        self.assertContains(r,'Co-Lead')
        self.assertContains(r,'Chapter Lead')
    def test_work_can_be_associated_with_unit(self):
        w=Work.objects.create(title='Venue plan',unit=self.conference,created_by=self.person)
        self.assertEqual(w.unit,self.conference)
