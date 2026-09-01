from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .api import PersonViewSet,GoalViewSet,WorkViewSet,DependencyViewSet,ActivityViewSet
router = DefaultRouter()
router.register("work", WorkViewSet, basename="work")
router.register("dependencies", DependencyViewSet, basename="dependency")
router.register("people", PersonViewSet, basename="person")
router.register("goals", GoalViewSet, basename="goal")
router.register("activity", ActivityViewSet, basename="activity")
urlpatterns=[
    path('',views.dashboard,name='dashboard'),
    path('organization/',views.organization,name='organization'),
    path('people/<int:pk>/',views.person_detail,name='person_detail'),
    path('board/',views.board,name='board'),
    path('board/reorder/',views.board_reorder,name='board_reorder'),
    path('my-work/',views.my_work_legacy,name='my_work'),
    path('work/new/',views.work_create,name='work_create'),
    path('work/<int:pk>/',views.work_detail,name='work_detail'),
    path('work/<int:pk>/edit/',views.work_edit,name='work_edit'),
    path('work/<int:pk>/status/',views.work_status,name='work_status'),
    path('api/',include(router.urls)),
    path('api/export/work.csv',views.export_work_csv,name='export_work_csv'),
    path('api/export/snapshot.json',views.export_snapshot_json,name='export_snapshot_json'),
]
