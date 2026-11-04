from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings
from .forms import DocumentUploadForm
from .models import Document, ExtractedData
import pytesseract
from PIL import Image
import os
import base64
from openai import OpenAI
from django.http import HttpResponse
import csv

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# OpenRouter setup
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

def upload(request):
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save()

            # step 1 - file saved
            document.file_saved = True
            document.status = 'processing'
            document.save()

            image_path = os.path.join(settings.MEDIA_ROOT, document.file.name)
            image = Image.open(image_path)

            # step 2 - tesseract
            try:
                raw_text = pytesseract.image_to_string(image)
                ExtractedData.objects.create(
                    document=document,
                    provider='tesseract',
                    raw_text=raw_text,
                )
            except Exception as e:
                ExtractedData.objects.create(
                    document=document,
                    provider='tesseract',
                    raw_text=f"Tesseract error: {str(e)}",
                )
            document.tesseract_done = True
            document.save()

            # step 3 - gemini
            try:
                with open(image_path, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode("utf-8")

                response = client.chat.completions.create(
                    model="google/gemini-2.0-flash-lite-001",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_data}"
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": """You are an expert document analysis AI. Carefully examine this image and extract ALL text content with perfect accuracy.

                                        Format the output as follows:
                                        - Preserve the original structure and layout as much as possible
                                        - Group related information together (header info, line items, totals, etc.)
                                        - Maintain hierarchy — headings before details, items before totals
                                        - Separate distinct sections with a blank line
                                        - Preserve all numbers, dates, prices, and codes exactly as they appear
                                        - Do not summarize, skip, or paraphrase anything — extract everything you see

                                        Return only the extracted and organized text, nothing else."""
                                }
                            ]
                        }
                    ]
                )
                ExtractedData.objects.create(
                    document=document,
                    provider='gemini',
                    raw_text=response.choices[0].message.content,
                )
            except Exception as e:
                ExtractedData.objects.create(
                    document=document,
                    provider='gemini',
                    raw_text=f"Gemini error: {str(e)}",
                )
            document.gemini_done = True
            document.status = 'done'
            document.save()

            # return document id so browser can poll
            return JsonResponse({'document_id': document.pk})
    else:
        form = DocumentUploadForm()

    return render(request, 'invoices/upload.html', {'form': form})


def progress(request, pk):
    document = Document.objects.get(pk=pk)
    return JsonResponse({
        'file_saved': document.file_saved,
        'tesseract_done': document.tesseract_done,
        'gemini_done': document.gemini_done,
        'status': document.status,
    })


def result(request, pk):
    document = Document.objects.get(pk=pk)
    tesseract_data = document.extracted_set.filter(provider='tesseract').first()
    gemini_data = document.extracted_set.filter(provider='gemini').first()
    return render(request, 'invoices/result.html', {
        'document': document,
        'tesseract_data': tesseract_data,
        'gemini_data': gemini_data,
    })


def history(request):
    documents = Document.objects.all().order_by('-uploaded_at')
    return render(request , 'invoices/history.html',{ 'documents': documents })


def export(request, pk , provider , format):
    document = Document.objects.get(pk=pk)
    data = document.extracted_set.filter(provider=provider).first()

    if not data:
        return HttpResponse("No data found", status=404)
    
    filename = f"document_{pk}_{provider}"

    if format == 'txt':
        response = HttpResponse(data.raw_text, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{filename}.txt"'
        return response

    elif format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Provider', 'Extracted Text'])
        writer.writerow([provider, data.raw_text])
        return response

    return HttpResponse("Invalid format", status=400)