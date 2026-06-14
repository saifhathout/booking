from django import forms
from .models import Venue, Field, VenueSlot

class VenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ['name', 'address', 'city', 'sport_type', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'sport_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class FieldForm(forms.ModelForm):
    class Meta:
        model = Field
        fields = ['name', 'sport_type', 'description', 'price_per_hour', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'sport_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price_per_hour': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class VenueSlotForm(forms.ModelForm):
    class Meta:
        model = VenueSlot
        fields = ['field', 'date', 'start_time', 'end_time']
        widgets = {
            'field': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }
    
    def __init__(self, *args, **kwargs):
        venue = kwargs.pop('venue', None)
        super().__init__(*args, **kwargs)
        if venue:
            self.fields['field'].queryset = Field.objects.filter(venue=venue)