from django.utils.translation import gettext_lazy as _
from django import forms
import django.core.exceptions
import django.contrib.auth.forms
import django.contrib.auth.password_validation

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Field, HTML, Hidden
import crispy_forms.bootstrap

from . import models


class FormActions(crispy_forms.bootstrap.FormActions):
    def __init__(self, *fields, **kwargs):
        kwargs["css_class"] = "form-group " + kwargs.get("css_class", "")
        super().__init__(*fields, **kwargs)


class CoreFieldsMixin(forms.Form):
    username = forms.CharField(
        label=_("Username"),
        max_length=20,
        help_text=_("Unique, no spaces, max 20 characters"),
        validators=[models.validate_username],
    )
    password = forms.CharField(
        label=_("Password"),
        min_length=8,
        max_length=255,
        help_text=_("At least 8 characters"),
        widget=forms.PasswordInput(render_value=True),
    )
    email = forms.EmailField(label=_("Email"), max_length=255, help_text=_("Never displayed publicly"))

    login_type = forms.CharField(widget=forms.HiddenInput(), required=False)


class ProfileFieldsMixin(forms.Form):
    full_name = forms.CharField(
        label=_("Full Name"), max_length=255, required=False, help_text=_("Enter your full name here")
    )
    mc_username = forms.CharField(
        label=_("XBox GameTag"),
        max_length=255,
        required=False,
        help_text=_("Enter the username you use for Minecraft here"),
    )
    irc_nick = forms.CharField(
        label=_("IRC Nick"),
        max_length=255,
        required=False,
        help_text=_("Join us on IRC often? Enter your IRC nick here"),
    )
    gh_username = forms.CharField(
        label=_("GitHub Username"),
        max_length=255,
        required=False,
        help_text=_("Publish your software on GitHub? " "Enter your GitHub username here"),
    )
    discord_id = forms.CharField(
        label=_("Discord ID"),
        max_length=255,
        required=False,
        help_text=_("You're using Discord?" "Enter your Discord ID here"),
        validators=[models.validate_discord_id],
    )


class RegistrationMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        toses = models.TermsOfService.objects.filter(current_tos=True)
        self.tos_fields = {}
        for tos in toses:
            field_name = "accept_tos_{}".format(tos.id)
            self.tos_fields[field_name] = tos
            self.fields[field_name] = forms.BooleanField(
                required=True, label='I agree to the <a href="{}">{}</a>'.format(tos.tos_url, tos.name)
            )

    def clean_username(self):
        username = self.cleaned_data["username"]
        if models.User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(_("A user with that username already exists."))
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if models.User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("A user with that email already exists."))
        return email

    def clean(self):
        cleaned_data = super().clean()
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        email = self.cleaned_data.get("email")
        if username and password and email:
            user = models.User(username=username, password=password, email=email)
            try:
                django.contrib.auth.password_validation.validate_password(password, user=user)
            except forms.ValidationError as ve:
                self.add_error("password", ve)
        return cleaned_data


class RegisterGoogleForm(ProfileFieldsMixin, CoreFieldsMixin, RegistrationMixin, forms.Form):
    google_id_token = forms.CharField(widget=forms.HiddenInput())

    form_submitted = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        email_editable = kwargs.pop("email_editable", False)
        super().__init__(*args, **kwargs)
        if not email_editable:
            self.fields["email"].disabled = True
            self.fields["email"].widget.attrs["readonly"] = True
        del self.fields["password"]
        self.fields["login_type"].initial = "google"
        self.fields["form_submitted"].initial = "yes"

        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", _("Sign up"), css_class="pull-right"))


class RegisterForm(ProfileFieldsMixin, CoreFieldsMixin, RegistrationMixin, forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        fields = [
            Field("username"),
            Field("password"),
            Field("email"),
            Field("full_name"),
            Field("mc_username"),
            Field("irc_nick"),
            Field("gh_username"),
            Field("discord_id"),
        ]
        for field in getattr(self, "tos_fields", {}).keys():
            fields.append(Field(field))
        fields += [
            FormActions(
                HTML(
                    """<a href="{{% url 'accounts:login' %}}" """
                    """class="btn btn-default">{}</a> """.format(_("Log in"))
                ),
                Submit("sign up", _("Sign up")),
                css_class="pull-right",
            )
        ]
        self.helper.layout = Layout(*fields)


class AuthenticationForm(forms.Form):
    username = forms.CharField(label=_("Username"), max_length=20)
    password = forms.CharField(label=_("Password"), max_length=255, widget=forms.PasswordInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field("username"),
            HTML(
                """<i class="pull-right forgot-link">"""
                """<a tabindex="-1" href="{{% url 'accounts:forgot' %}}">"""
                """{}</a></i>""".format(_("Forgot your password?"))
            ),
            Field("password"),
            HTML(
                """<div class="g-signin2 pull-left" """
                """data-onsuccess="onGoogleSignIn" """
                """data-theme="dark"></div>"""
            ),
            FormActions(
                HTML(
                    """<a href="{{% url 'accounts:register' %}}" """
                    """class="btn btn-default">{}</a> """.format(_("Sign up"))
                ),
                Submit("log in", _("Log in")),
                css_class="pull-right",
            ),
        )

    def clean_username(self):
        # this allows user enumeration by username,
        # but it's easy enough to find usernames anyway
        # so I'm not especially concerned
        username = self.cleaned_data["username"]
        if not models.User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(_("There is no user with that username."))
        return username

    def clean(self):
        cleaned_data = super().clean()
        self.cached_user = None
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")

        if username and password:
            user = django.contrib.auth.authenticate(username=username, password=password)
            self.cached_user = user
            if not user:
                self.add_error("password", _("The provided password was incorrect."))

        return cleaned_data


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(label="Email", max_length=255)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(Field("email"), Submit("reset", _("Send me that link!"), css_class="pull-right"))


class ForgotPasswordSetForm(forms.Form):
    password = forms.CharField(
        label=_("New Password"),
        min_length=8,
        max_length=255,
        help_text=_("At least 8 characters"),
        widget=forms.PasswordInput(render_value=True),
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(Field("password"), Submit("reset", _("Reset my password"), css_class="pull-right"))

    def clean_password(self):
        password = self.cleaned_data["password"]
        django.contrib.auth.password_validation.validate_password(password, user=self.user)
        return password


class ProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit("profile-save", _("Save changes"), css_class="pull-right"))
        self.helper.add_input(Hidden("form", "profile"))

    class Meta:
        model = models.User
        fields = ["full_name", "mc_username", "irc_nick", "gh_username", "discord_id"]


class ChangePasswordForm(forms.Form):
    new_password = forms.CharField(
        label=_("New password"),
        min_length=8,
        max_length=255,
        help_text=_("At least 8 characters"),
        widget=forms.PasswordInput(render_value=True),
    )
    old_password = forms.CharField(
        label=_("Old password"), max_length=255, widget=forms.PasswordInput(render_value=True)
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit("password-save", _("Change password"), css_class="pull-right"))
        self.helper.add_input(Hidden("form", "password"))

    def clean_old_password(self):
        old_password = self.cleaned_data["old_password"]
        if not self.user.check_password(old_password):
            raise forms.ValidationError(_("This password is incorrect."))
        return old_password

    def clean_new_password(self):
        password = self.cleaned_data["new_password"]
        django.contrib.auth.password_validation.validate_password(password, user=self.user)
        return password


class SetAvatarForm(forms.Form):
    UPLOAD = "upload"
    GRAVATAR = "gravatar"
    LETTER = "letter"
    SOURCE_CHOICES = ((LETTER, _("Default avatar")), (UPLOAD, _("Uploaded avatar")), (GRAVATAR, _("Use Gravatar")))

    avatar_from = forms.ChoiceField(choices=SOURCE_CHOICES, widget=forms.RadioSelect())
    avatar_image = forms.ImageField(required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field("avatar_from"),
            Field("avatar_image", css_class="avatar-image-upload"),
            Submit("avatar-save", _("Set avatar"), css_class="pull-right"),
            Hidden("form", "avatar"),
        )

    def clean(self):
        cleaned_data = super().clean()
        avatar_from = cleaned_data.get("avatar_from")
        avatar_image = cleaned_data.get("avatar_image")
        if avatar_from == self.UPLOAD and not avatar_image:
            self.add_error(
                "avatar_image",
                forms.ValidationError(self.fields["avatar_image"].error_messages["required"], code="required"),
            )
        return cleaned_data


class ChangeEmailForm(forms.Form):
    new_email = forms.EmailField(label=_("New email"))

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit("save", _("Change email"), css_class="pull-right"))

    def clean_new_email(self):
        old_email = self.user.email
        new_email = self.cleaned_data["new_email"]
        if old_email == new_email:
            raise forms.ValidationError(_("Your new email must be different to your old email."))
        return new_email
