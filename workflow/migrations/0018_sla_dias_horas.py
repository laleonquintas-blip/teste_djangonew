from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workflow', '0017_add_configuracao_sla'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracaosla',
            name='prazo_dias',
            field=models.PositiveIntegerField(default=0, verbose_name='Prazo (dias)', help_text='Parte em dias do prazo máximo permitido neste status.'),
        ),
        migrations.AlterField(
            model_name='configuracaosla',
            name='prazo_horas',
            field=models.PositiveIntegerField(default=0, verbose_name='Prazo (horas)', help_text='Parte em horas (0-23) do prazo máximo permitido neste status.'),
        ),
    ]
