from django import forms
from .models import Venue, Field, VenueSlot

class VenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ['name', 'address', 'city', 'sport_type', 'description']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'input-fire'})


class FieldForm(forms.ModelForm):
    class Meta:
        model = Field
        fields = ['name', 'sport_type', 'description', 'price_per_hour', 'is_active']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if field.widget.__class__.__name__ == 'CheckboxInput':
                field.widget.attrs.update({'class': 'w-5 h-5 accent-[#00FF88]'})
            else:
                field.widget.attrs.update({'class': 'input-fire'})


class VenueSlotForm(forms.ModelForm):
    class Meta:
        model = VenueSlot
        fields = ['field', 'date', 'start_time', 'end_time']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }
    
    def __init__(self, *args, **kwargs):
        venue = kwargs.pop('venue', None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'input-fire'})
        if venue:
            self.fields['field'].queryset = Field.objects.filter(venue=venue)