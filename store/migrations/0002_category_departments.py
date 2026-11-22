from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('store', '0001_initial')]
    operations = [
        migrations.AlterField(
            model_name='category',
            name='department',
            field=models.CharField(choices=[('men','Men'),('women','Women'),('kids','Kids'),('accessories','Accessories'),('footwear','Footwear'),('watches','Watches')], max_length=20),
        ),
    ]
