from clinica.models import PlantillaTarea


def plantillas_para_sede(servicio, sede):
    local = PlantillaTarea.objects.filter(servicio=servicio, sede=sede)
    qs = local if local.exists() else PlantillaTarea.objects.filter(servicio=servicio, sede__isnull=True)
    version = qs.order_by('-version').values_list('version', flat=True).first() or 1
    return qs.filter(version=version).order_by('orden'), version
