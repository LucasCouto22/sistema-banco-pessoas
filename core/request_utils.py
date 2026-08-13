def ip_cliente(request):
    """IP real de quem fez a requisição. `REMOTE_ADDR` sozinho não serve em
    produção: o Railway (e qualquer proxy reverso) termina a conexão na
    borda, então `REMOTE_ADDR` sempre seria o IP interno do proxy, não o do
    participante — por isso prioriza `X-Forwarded-For` (primeiro IP da
    cadeia, que é o do cliente original) e só cai pra `REMOTE_ADDR` se esse
    cabeçalho não existir (ex.: rodando local, sem proxy na frente)."""
    encaminhado = request.META.get("HTTP_X_FORWARDED_FOR")
    if encaminhado:
        return encaminhado.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
