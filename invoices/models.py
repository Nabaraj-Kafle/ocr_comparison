from django.db import models

class Document(models.Model):
    file = models.ImageField(upload_to = 'invoices/' )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    STATUS_CHOICES = [
        ('pending','Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed'),

    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES , default='pending')


    # progress 
    file_saved = models.BooleanField(default=False)
    tesseract_done = models.BooleanField(default=False)
    gemini_done = models.BooleanField(default=False)


    def __str__(self):
        return f"Document {self.id} - {self.status}"
    

class ExtractedData(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='extracted_set')    
    provider = models.CharField(max_length=60)
    raw_text = models.TextField(blank=True)
    structured_data = models.JSONField(null=True , blank=True)
    extracted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Extracted via {self.provider} for Document {self.document.id}"