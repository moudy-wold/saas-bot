from django import forms


class LoginForm(forms.Form):
    tenant_slug = forms.CharField(max_length=100)
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)


class TenantCreateForm(forms.Form):
    tenant_name = forms.CharField(max_length=150)
    tenant_slug = forms.CharField(max_length=100)
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput, min_length=6)
    confirm_password = forms.CharField(widget=forms.PasswordInput, min_length=6)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Password and confirm password do not match")
        return cleaned_data


class GeneralSettingsForm(forms.Form):
    bot_token = forms.CharField(max_length=255)
    webhook_url = forms.URLField()


class FormJsonForm(forms.Form):
    form_json = forms.CharField(widget=forms.Textarea(attrs={"rows": 18}))


class BotProfileJsonForm(forms.Form):
    bot_profile_json = forms.CharField(widget=forms.Textarea(attrs={"rows": 22}))
