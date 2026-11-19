<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<style>
  @page { margin: 18mm 20mm 22mm 20mm; }
  body { font-family: Helvetica, Arial, sans-serif; font-size: 9pt; color: #1c1e21; margin: 0; }
  table { border-collapse: collapse; }
  .muted { color: #6b7280; }
  .faint { color: #9ca3af; }
  .co { font-size: 8.5pt; line-height: 1.35; color: #6b7280; }
  .co-name { font-size: 18pt; font-weight: bold; color: #1c1e21; }
  .doc-title { font-size: 22pt; font-weight: bold; color: #111827; text-align: right; line-height: 1.05; }
  .doc-sub { font-size: 9pt; color: #6b7280; text-align: right; }
  .doc-code { font-size: 13pt; font-weight: bold; color: #0a63e2; text-align: right; margin-top: 2mm; }
  .rule { border-top: 2px solid #0a63e2; margin: 4mm 0 5mm 0; height: 0; }
  .boxes { width: 100%; background: #f4f5f7; border-left: 2.5pt solid #0a63e2; }
  .boxes td { vertical-align: top; padding: 9px 10px; }
  .lbl { font-size: 7.5pt; font-weight: bold; color: #9ca3af; }
  .cname { font-size: 11pt; font-weight: bold; color: #111827; margin: 1px 0 2px 0; }
  .ctext { font-size: 9pt; color: #6b7280; line-height: 1.3; }
  .det td { padding: 1px 0; font-size: 8.5pt; }
  .det .v { text-align: right; font-weight: bold; color: #1c1e21; font-size: 9pt; }
  .det .k { color: #9ca3af; }
  table.items { width: 100%; margin-top: 7mm; }
  table.items th { background: #111827; color: #fff; font-size: 8pt; padding: 6px 8px; text-align: right; }
  table.items td { padding: 6px 8px; font-size: 9pt; border-bottom: 0.5pt solid #e5e7eb; text-align: right; vertical-align: middle; }
  table.items tr.alt td { background: #fafafb; }
  .l { text-align: left !important; }
  .c { text-align: center !important; }
  .num { color: #9ca3af; }
  .note { font-size: 7.5pt; color: #9ca3af; font-style: italic; }
  table.totals { margin: 5mm 0 0 auto; width: 54%; }
  table.totals td { text-align: right; padding: 3px 8px; font-size: 9pt; color: #6b7280; }
  table.totals tr.grand td { background: #111827; color: #fff; font-weight: bold; font-size: 11pt; padding: 7px 8px; }
  .section { background: #f4f5f7; border-left: 2.5pt solid #0a63e2; padding: 8px 10px; margin-top: 7mm; }
  .section .t { font-size: 7.5pt; font-weight: bold; color: #9ca3af; margin-bottom: 3px; }
  .section .p { font-size: 9pt; color: #6b7280; line-height: 1.35; }
  .closing { text-align: center; color: #6b7280; margin-top: 8mm; font-size: 9pt; }
  .annex-h { font-size: 13pt; font-weight: bold; margin: 0 0 2px 0; page-break-before: always; }
  .annex-c { font-size: 8.5pt; color: #6b7280; }
  .photo { position: relative; margin-top: 4mm; }
  .pin { position: absolute; background: #0a63e2; border: 1.2pt solid #fff; color: #fff; font-weight: bold; text-align: center; border-radius: 50%; }
  .legend td { padding: 1px 0; font-size: 9pt; }
  .legend .n { color: #0a63e2; font-weight: bold; width: 10mm; }
  .block { page-break-inside: avoid; margin-bottom: 8mm; }
</style>
</head>
<body>

<table style="width:100%">
  <tr>
    <td style="width:58%; vertical-align:top">
      @if($logo)
        <img src="{{ $logo['uri'] }}" style="width:{{ $logo['w'] }}mm; height:{{ $logo['h'] }}mm" alt="">
      @else
        <div class="co-name">{{ $company['name'] }}</div>
        @if($company['tagline'])<div class="co">{{ $company['tagline'] }}</div>@endif
      @endif
      @if($company['representative'])<div class="co">{{ $company['representative'] }}</div>@endif
      @foreach($companyLines as $line)<div class="co">{{ $line }}</div>@endforeach
    </td>
    <td style="width:42%; vertical-align:top">
      <div class="doc-title">{{ mb_strtoupper($mainTitle) }}</div>
      @if($subtitle)<div class="doc-sub">{{ $subtitle }}</div>@endif
      <div class="doc-code">{{ $code }}</div>
    </td>
  </tr>
</table>
<div class="rule"></div>

<table class="boxes">
  <tr>
    <td style="width:55%">
      <div class="lbl">{{ $clientLabel }}</div>
      <div class="cname">{{ $client->name }}</div>
      @if($client->company)<div class="ctext">{{ $client->company }}</div>@endif
      @if($client->rnc)<div class="ctext">RNC: {{ $client->rnc }}</div>@endif
      @if($client->address)<div class="ctext">{{ $client->address }}</div>@endif
      @if($client->phone)<div class="ctext">{{ $client->phone }}</div>@endif
    </td>
    <td style="width:45%">
      <table class="det" style="width:100%">
        @foreach($details as [$k, $v])
          <tr><td class="k">{{ $k }}</td><td class="v">{{ $v }}</td></tr>
        @endforeach
      </table>
    </td>
  </tr>
</table>

@if($categoryTotals !== null)
  <table class="items">
    <thead><tr><th class="l" style="width:77%">Categoría</th><th style="width:23%">Subtotal</th></tr></thead>
    @foreach($categoryTotals as $i => [$name, $amount])
      <tr class="{{ $i % 2 ? 'alt' : '' }}"><td class="l">{{ $name }}</td><td>{{ $fmt($amount) }}</td></tr>
    @endforeach
  </table>
@elseif($showLinePrices)
  <table class="items">
    <thead><tr><th class="c" style="width:6%">#</th><th class="l" style="width:45%">Descripción</th><th style="width:10%">Cant.</th><th style="width:18%">Precio unit.</th><th style="width:21%">Importe</th></tr></thead>
    @foreach($items as $i => $it)
      <tr class="{{ $i % 2 ? 'alt' : '' }}">
        <td class="c num">{{ $i + 1 }}</td>
        <td class="l">{{ $it['description'] }}@if($it['note'])<br><span class="note">{{ $it['note'] }}</span>@endif</td>
        <td>{{ $qty($it['quantity']) }}</td><td>{{ $fmt($it['unit_price']) }}</td><td>{{ $fmt($it['subtotal']) }}</td>
      </tr>
    @endforeach
  </table>
@elseif($showQuantities && $quantityFirst)
  <table class="items">
    <thead><tr><th class="l" style="width:12%">Cant.</th><th class="l" style="width:88%">Descripción</th></tr></thead>
    @foreach($items as $i => $it)
      <tr class="{{ $i % 2 ? 'alt' : '' }}"><td class="l">{{ $qty($it['quantity']) }}</td>
        <td class="l">{{ $it['description'] }}@if($it['note'])<br><span class="note">{{ $it['note'] }}</span>@endif</td></tr>
    @endforeach
  </table>
@elseif($showQuantities)
  <table class="items">
    <thead><tr><th class="l" style="width:88%">Descripción</th><th style="width:12%">Cant.</th></tr></thead>
    @foreach($items as $i => $it)
      <tr class="{{ $i % 2 ? 'alt' : '' }}">
        <td class="l">{{ $it['description'] }}@if($it['note'])<br><span class="note">{{ $it['note'] }}</span>@endif</td>
        <td>{{ $qty($it['quantity']) }}</td></tr>
    @endforeach
  </table>
@else
  <table class="items">
    <thead><tr><th class="l">Descripción</th></tr></thead>
    @foreach($items as $i => $it)
      <tr class="{{ $i % 2 ? 'alt' : '' }}"><td class="l">{{ $it['description'] }}@if($it['note'])<br><span class="note">{{ $it['note'] }}</span>@endif</td></tr>
    @endforeach
  </table>
@endif

@if($showBreakdown)
  <table class="totals">
    @if($showLinePrices || $categoryTotals !== null)
      <tr><td>Subtotal</td><td>{{ $fmt($subtotal) }}</td></tr>
      <tr><td>ITBIS ({{ $itbisPct }}%)</td><td>{{ $fmt($itbis) }}</td></tr>
      <tr class="grand"><td>TOTAL</td><td>{{ $fmt($total) }}</td></tr>
    @else
      <tr class="grand"><td>TOTAL DEL SERVICIO</td><td>{{ $fmt($total) }}</td></tr>
    @endif
  </table>
@endif

@if($notes)
  <div class="section"><div class="t">NOTAS</div><div class="p">{!! nl2br(e($notes)) !!}</div></div>
@endif
@if($bankLines)
  <div class="section"><div class="t">DATOS PARA DEPÓSITO O TRANSFERENCIA</div>
    @foreach($bankLines as $l)<div class="p">{{ $l }}</div>@endforeach
  </div>
@endif
@if($closingNote)<div class="closing">{{ $closingNote }}</div>@endif

@if(count($annex))
  <div class="annex-h">Anexo: ubicación de los equipos</div>
  <div class="annex-c">Fotos del levantamiento con los puntos numerados.</div>
  @foreach($annex as $i => $ph)
    <div class="block">
      <div class="photo" style="width:{{ $ph['w'] }}mm; height:{{ $ph['h'] }}mm">
        <img src="{{ $ph['uri'] }}" style="width:{{ $ph['w'] }}mm; height:{{ $ph['h'] }}mm" alt="">
        @foreach($ph['pins'] as $pin)
          <div class="pin" style="left:{{ $pin['left'] }}mm; top:{{ $pin['top'] }}mm; width:{{ $pin['d'] }}mm; height:{{ $pin['d'] }}mm; line-height:{{ $pin['d'] }}mm; font-size:{{ $pin['font'] }}pt">{{ $pin['n'] }}</div>
        @endforeach
      </div>
      <div class="annex-c" style="margin-top:2mm">{{ $ph['title'] ?: 'Foto '.($i + 1) }}</div>
      @if(count($ph['legend']))
        <table class="legend" style="margin-top:1.5mm; width:100%">
          @foreach($ph['legend'] as [$n, $label])<tr><td class="n">{{ $n }}</td><td>{{ $label ?: 'Punto sin nombre' }}</td></tr>@endforeach
        </table>
      @endif
    </div>
  @endforeach
@endif

</body>
</html>
