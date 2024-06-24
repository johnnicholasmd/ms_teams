from django import forms


class DateFilterForm(forms.Form):
    start_date = forms.DateTimeField(label="Start date", widget=forms.widgets.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateTimeField(label="End date", widget=forms.widgets.DateInput(attrs={'type': 'date'}))