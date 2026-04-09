from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('expenses', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Receipt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='receipts/')),
                ('extracted_text', models.TextField(blank=True, default='')),
                ('raw_ocr_response', models.JSONField(blank=True, default=dict)),
                ('processing_status', models.CharField(choices=[('pending', 'Pending'), ('success', 'Success'), ('failed', 'Failed')], default='pending', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='receipts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'receipts',
                'verbose_name': 'Receipt',
                'verbose_name_plural': 'Receipts',
                'ordering': ['-created_at'],
            },
        ),
    ]