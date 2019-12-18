import base64

from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Field, Hidden

from . import models
from . import oath

TOTP_TOLERANCE = 1


class TOTPVerifyForm(forms.Form):
    response = forms.IntegerField(label=_("Code"), min_value=0, max_value=999_999)

    def __init__(self, *args, **kwargs):
        device = kwargs.pop("device")
        self.device = device

        signed_secret = kwargs.pop("secret", None)  # used for setup flow
        self.secret = signed_secret

        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        submit = Submit("submit", _("Log in"), css_class="pull-right")
        self.helper.layout = Layout(Field("response", autofocus="autofocus"), submit)

        if signed_secret:
            self.helper.layout.append(Hidden("secret", signed_secret))
            submit.value = _("Add authenticator")

    def clean_response(self):
        code = self.cleaned_data["response"]
        verifier = oath.TOTP(base64.b32decode(self.device.base32_secret), drift=self.device.drift)
        # lock verifier to now
        verifier.time = verifier.time
        last_t = self.device.last_t or -1
        ok = verifier.verify(code, tolerance=TOTP_TOLERANCE, min_t=last_t + 1)
        if not ok:
            raise forms.ValidationError(_("That code could not be verified."))

        # persist data
        self.device.last_t = verifier.t()
        self.device.drift = verifier.drift
        self.device.last_used_at = timezone.now()
        self.device.save()

        return code


class PaperVerifyForm(forms.Form):
    response = forms.CharField(label=_("Recovery code"), max_length=8, min_length=8)

    def __init__(self, *args, **kwargs):
        device = kwargs.pop("device")
        self.device = device

        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        submit = Submit("submit", _("Log in"), css_class="pull-right")
        self.helper.layout = Layout(Field("response", autofocus="autofocus"), submit)

    def clean_response(self):
        code = self.cleaned_data["response"]
        try:
            code_obj = self.device.codes.get(code=code)
        except models.PaperCode.DoesNotExist:
            raise forms.ValidationError(_("That code is incorrect."))

        if code_obj.used_at:
            raise forms.ValidationError(_("That code has already been used."))

        # mark as used
        code_obj.used_at = timezone.now()
        code_obj.save()
        self.device.last_used_at = timezone.now()
        self.device.save()

        return code
