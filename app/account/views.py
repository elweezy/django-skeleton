from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.forms.util import ErrorList
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import render, redirect, render_to_response, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
import django.contrib.auth as django_auth
import hashlib
import datetime
import random
from django.utils import timezone
from core.utils.decorators import log, anonymous_required
from . import models
from . import forms


def index(request, template="user/account/index.html", context={}):
    return render(request, template, context)


@log
@anonymous_required
def login(request, template="user/account/login.html", context={}):
    next_url = request.GET.get('next', False)
    login_form = forms.LoginForm(request.POST or None)

    if request.method == 'POST':
        if login_form.is_valid():
            username = login_form.cleaned_data['username']
            password = login_form.cleaned_data['password']
            user = django_auth.authenticate(username=username, password=password)
            if user is not None:
                if user.is_active:
                    django_auth.login(request, user)
                    messages.add_message(request, messages.SUCCESS, _('You have successfully logged in.'))
                    if next_url:
                        return redirect(next_url)
                    else:
                        return redirect(reverse('home'))
                else:
                    messages.add_message(request, messages.WARNING, _('Non active user.'))
            else:
                messages.add_message(request, messages.ERROR, _('Wrong username or password.'))

    context['login_form'] = login_form
    return render(request, template, context)


@log
@anonymous_required
def register(request, template="user/account/register.html", context={}):
    user_form = forms.UserForm(request.POST or None)
    profile_form = forms.ProfileForm(request.POST or None, request.FILES or None)

    if request.method == 'POST':
        if user_form.is_valid() and profile_form.is_valid():
            user_username = user_form.cleaned_data['username']
            user_email = user_form.cleaned_data['email']
            user_password = user_form.cleaned_data['password']
            salt = hashlib.sha1(str(random.random())).hexdigest()[:5]
            activation_key = hashlib.sha1(salt+user_email).hexdigest()
            key_expires = datetime.datetime.today() + datetime.timedelta(2)

            user = user_form.save(commit=False)
            if user.email and User.objects.filter(email=user_email).exclude(username=user_username).count():
                errors = user_form._errors.setdefault("email", ErrorList())
                errors.append(_('User with this Email already exists.'))
                messages.add_message(request, messages.ERROR, _('Please fix errors bellow.'))
            else:
                user.set_password(user_password)
                user.save()
                profile = profile_form.save(commit=False)
                profile.user = user
                profile.activation_key = activation_key
                profile.key_expires = key_expires
                profile.save()
                messages.add_message(request, messages.SUCCESS, _('You have successfully registered.'))
                user = django_auth.authenticate(username=user_username, password=user_password)
                django_auth.login(request, user)

                # Send email with activation key
                email_subject = 'Account confirmation'
                email_body = "Hey %s, thanks for signing up. To activate your account, click this link within 48hours" \
                             "\nhttp://localhost:8000/account/confirm/%s" % (user_username, activation_key)

                send_mail(email_subject, email_body, "noreply@tapdoon.email", [user_email], fail_silently=False)

                return redirect(reverse('account_index'))
        else:
            messages.add_message(request, messages.ERROR, _('Please fix errors bellow.'))

    context['user_form'] = user_form
    context['profile_form'] = profile_form
    context['forms'] = (user_form, profile_form, )

    return render(request, template, context)


def register_confirm(request, activation_key):
    if request.user.is_authenticated():
        HttpResponseRedirect('/blog/index/')

    user_profile = get_object_or_404(models.Profile, activation_key=activation_key)

    if user_profile.key_expires < timezone.now():
        return render_to_response('user/account/confirm_expired.html')

    user_profile.is_verified = True
    user_profile.save()

    return render_to_response('user/account/confirm.html')


def email_change_confirm(request, activation_key):
    if request.user.is_authenticated():
        HttpResponseRedirect('/blog/index/')

    email_change_request = get_object_or_404(models.EmailChangeRequest, activation_key=activation_key)

    if email_change_request.key_expires < timezone.now():
        return render_to_response('user/account/confirm_expired.html')

    user_profile = get_object_or_404(models.Profile, user=email_change_request.user)
    user_profile.is_verified = True
    user_profile.save()
    user = User.objects.get(id=user_profile.user.id)
    user.email = email_change_request.new_email
    user.save()

    return render_to_response('user/account/confirm.html')


@log
@login_required
def logout(request):
    django_auth.logout(request)
    messages.add_message(request, messages.SUCCESS, _('You have successfully logged out.'))
    return redirect(reverse('home'))


@log
def modify_account(request, template="user/account/account_modify.html", context={}):
    user_form = None
    profile_form = None

    if not hasattr(request.user, 'profile'):
        request.user.profile = models.Profile()

    if request.method == 'POST':
        user_form = forms.ModifyUserForm(request.POST or None, instance=request.user)
        profile_form = forms.ModifyProfileForm(request.POST or None, request.FILES or None,
            instance=request.user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.add_message(request, messages.SUCCESS, _('Your account successfully modified.'))
            return redirect(reverse('account_index'))
        else:
            messages.add_message(request, messages.ERROR, _('Some errors occurred. Please fix errors bellow.'))
    else:
        user = request.user
        user_form = forms.ModifyUserForm(instance=user)
        profile_form = forms.ModifyProfileForm(instance=user.profile)

    context['user_form'] = user_form
    context['profile_form'] = profile_form
    context['forms'] = (user_form, profile_form, )

    return render(request, template, context)

