from src.healthcheck import estado_entorno

def test_entorno_preparado():
    assert estado_entorno() == "listo"
    