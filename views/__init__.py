from .inventory import (
    mostrar_inventario_geral, 
    editar_item, 
    excluir_item, 
    marcar_para_thomas,
    adicionar_item_form
)

from .thomas import (
    mostrar_inventario_thomas,
    mostrar_perfil_thomas,
    mostrar_restricoes_alimentares,
    mostrar_necessidades_nutricionais,
    mostrar_analise_nutricional_thomas
)

from .reports import (
    mostrar_relatorios,
    mostrar_relatorio_precos,
    mostrar_relatorio_consumo,
    mostrar_relatorio_nutricional
)

from .consumption import (
    registrar_consumo,
    mostrar_categorias
)

from .shopping import (
    mostrar_planejamento_feira,
    planejar_compras,
    comparativo_mercados,
    analise_precos
)