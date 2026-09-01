# Third Party Stuff
from django import forms
from django.db.models import Q

# Spoken Tutorial Stuff
from creation.models import *
from spoken import config as spoken_config
import json
def jsonify(data):
    return json.loads(data.replace("u'", "'").replace("'", '"'))

class CDContentForm(forms.Form):
    foss_category = forms.ChoiceField(
        choices = [('', 'Select FOSS Category')],
        required = True,
        error_messages = {'required':'FOSS category field is required.'}
    )
    level = forms.ChoiceField(
        choices = [('', 'Select Level'), (0, 'All'), (1, 'Basic'), (2, 'Intermediate'), (3, 'Advanced')],
        required = True,
        error_messages = {'required':'Level field is required.'}
    )
    language = forms.MultipleChoiceField(
        required = True,
        error_messages = {'required':'Languages field is required.'},
        choices = [('', 'Select Languages')]
    )
    selected_foss = forms.CharField(
        required = True,
        error_messages = {'required': 'Add atleast one foss and language, before pressing "Create ZIP file" button'},
        widget=forms.HiddenInput()
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(CDContentForm, self).__init__(*args, **kwargs)
        #self.fields['language'].choices = ['nothing']
        allowed_roles = getattr(spoken_config, 'CD_CONTENT_ALLOWED_ROLES', [])
        bypass_download = False
        if user and user.is_authenticated() and user.pk:
            if user.is_superuser or user.groups.filter(name__in=allowed_roles).exists():
                bypass_download = True

        if bypass_download:
            healthfosslist = list(FossCategory.objects.filter(show_on_homepage=0, foss__contains='Health').values_list('id', 'foss'))
            foss_list = list(TutorialResource.objects.filter(
                Q(status=1) | Q(status=2),
                tutorial_detail__foss__show_on_homepage=1
            ).values_list('tutorial_detail__foss_id', 'tutorial_detail__foss__foss').order_by('tutorial_detail__foss__foss').distinct()) + healthfosslist
        else:
            healthfosslist = list(FossCategory.objects.filter(show_on_homepage=0, foss__contains='Health', download=True).values_list('id', 'foss'))
            foss_list = list(TutorialResource.objects.filter(
                Q(status=1) | Q(status=2),
                tutorial_detail__foss__show_on_homepage=1,
                tutorial_detail__foss__download=True
            ).values_list('tutorial_detail__foss_id', 'tutorial_detail__foss__foss').order_by('tutorial_detail__foss__foss').distinct()) + healthfosslist

        foss_choices = [('', 'Select FOSS Category')] + foss_list
        self.fields['foss_category'].choices = foss_choices
        if args:
            print("args out ",args)
            if ('foss_category' in args[0]) and ('level' in args[0]):
                print("args in ",args[0])
                if args[0]['foss_category'] and args[0]['foss_category'] != '' and args[0]['foss_category'] != 'None':
                    try:
                        tmp_level = int(args[0]['level'])
                    except:
                        tmp_level = ''
                    if tmp_level:
                        lang_recs = list(TutorialResource.objects.filter(Q(status = 1)|Q(status = 2), tutorial_detail__foss_id = int(args[0]['foss_category']), tutorial_detail__level_id = int(tmp_level)).values_list('language_id', 'language__name').order_by('language__name').distinct())
                    else:
                        lang_recs = list(TutorialResource.objects.filter(Q(status = 1)|Q(status = 2), tutorial_detail__foss_id = int(args[0]['foss_category'])).values_list('language_id', 'language__name').order_by('language__name').distinct())
                    self.fields['language'].choices = lang_recs
