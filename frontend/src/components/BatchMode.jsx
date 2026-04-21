import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import toast from 'react-hot-toast'
import axios from 'axios'
import styles from './BatchMode.module.css'

const CUSTOMER = {
  name: 'Gabriel Eduardo Santisteban Garcia',
  address: '',
  phone: '',
  email: '',
  tax_id: '78890774S',
}

function buildInvoice(receipt, index) {
  const today = new Date().toISOString().split('T')[0]
  const num = `FACT-${Date.now().toString().slice(-4)}-${String(index + 1).padStart(3, '0')}`
  return {
    invoice_number: num,
    simplified_invoice_number: receipt.simplified_invoice_number || '',
    date: receipt.date || today,
    due_date: null,
    currency: 'EUR',
    notes: receipt.notes || '',
    payment_terms: '',
    issuer: {
      name: receipt.vendor_name || 'Desconocido',
      address: receipt.vendor_address || '',
      phone: receipt.vendor_phone || '',
      email: '',
      tax_id: receipt.vendor_tax_id || '',
    },
    client: CUSTOMER,
    items: receipt.items?.length
      ? receipt.items
      : [{ description: 'Compra', quantity: 1, unit_price: receipt.total || 0, total: receipt.total || 0 }],
    subtotal: receipt.subtotal ?? receipt.total ?? 0,
    tax_rate: receipt.tax && receipt.subtotal ? parseFloat(((receipt.tax / receipt.subtotal) * 100).toFixed(1)) : 0,
    tax_amount: receipt.tax ?? 0,
    total: receipt.total ?? 0,
  }
}

export default function BatchMode({ onBack }) {
  const [files, setFiles] = useState([])
  const [processing, setProcessing] = useState(false)
  const [results, setResults] = useState(null)
  const [generating, setGenerating] = useState(false)

  const onDrop = useCallback((accepted) => {
    setFiles((prev) => [...prev, ...accepted])
    setResults(null)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.webp'], 'application/pdf': ['.pdf'] },
    multiple: true,
    maxFiles: 20,
  })

  function removeFile(index) {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }

  async function processAll() {
    if (!files.length) return
    setProcessing(true)
    const toastId = toast.loading(`Procesando ${files.length} tickets...`)

    const formData = new FormData()
    files.forEach((f) => formData.append('files', f))

    try {
      const res = await axios.post('/api/receipts/analyze-batch', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 300000, // 5 min for batch
      })
      setResults(res.data.results)
      toast.success(`${res.data.success_count}/${res.data.total} procesados`, { id: toastId })
    } catch (err) {
      let msg = err.message
      if (err.response?.data?.detail) msg = err.response.data.detail
      toast.error(`Error: ${msg}`, { id: toastId })
    } finally {
      setProcessing(false)
    }
  }

  async function downloadAll() {
    const successResults = results.filter((r) => r.success)
    if (!successResults.length) return

    setGenerating(true)
    const toastId = toast.loading('Generando facturas PDF...')

    const invoices = successResults.map((r, i) => buildInvoice(r.data, i))

    try {
      const res = await axios.post('/api/invoices/generate-batch', { invoices }, { responseType: 'blob', timeout: 120000 })
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/zip' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `facturas-${new Date().toISOString().split('T')[0]}.zip`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('Facturas descargadas!', { id: toastId })
    } catch (err) {
      toast.error(`Error: ${err.message}`, { id: toastId })
    } finally {
      setGenerating(false)
    }
  }

  async function downloadSingle(result, index) {
    const invoice = buildInvoice(result.data, index)
    const toastId = toast.loading('Generando PDF...')
    try {
      const res = await axios.post('/api/invoices/generate', invoice, { responseType: 'blob' })
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `factura-${invoice.invoice_number}.pdf`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('Descargada', { id: toastId })
    } catch (err) {
      toast.error(`Error: ${err.message}`, { id: toastId })
    }
  }

  const successCount = results ? results.filter((r) => r.success).length : 0

  return (
    <div className={styles.container}>
      <div className={styles.titleRow}>
        <div>
          <h2 className={styles.title}>Procesamiento por lotes</h2>
          <p className={styles.subtitle}>Sube múltiples tickets y genera todas las facturas de una vez</p>
        </div>
        <button className={styles.backBtn} onClick={onBack}>← Modo individual</button>
      </div>

      {/* Drop zone */}
      <div {...getRootProps()} className={`${styles.dropzone} ${isDragActive ? styles.dropzoneActive : ''}`}>
        <input {...getInputProps()} />
        <div className={styles.dropContent}>
          <div className={styles.dropIcon}>📄</div>
          <p className={styles.dropText}>
            {isDragActive ? 'Suelta los archivos aquí' : 'Arrastra tickets aquí o haz clic para seleccionar'}
          </p>
          <span className={styles.dropHint}>JPG, PNG, PDF · Máximo 20 archivos</span>
        </div>
      </div>

      {/* File list */}
      {files.length > 0 && !results && (
        <div className={styles.fileList}>
          <div className={styles.fileListHeader}>
            <span>{files.length} archivo{files.length !== 1 ? 's' : ''} seleccionado{files.length !== 1 ? 's' : ''}</span>
            <button className={styles.clearBtn} onClick={() => setFiles([])}>Limpiar</button>
          </div>
          {files.map((f, i) => (
            <div key={i} className={styles.fileItem}>
              <span className={styles.fileName}>{f.name}</span>
              <span className={styles.fileSize}>{(f.size / 1024).toFixed(0)} KB</span>
              <button className={styles.removeBtn} onClick={() => removeFile(i)}>✕</button>
            </div>
          ))}
          <button className={styles.processBtn} onClick={processAll} disabled={processing}>
            {processing ? 'Procesando...' : `⚡ Procesar ${files.length} tickets`}
          </button>
        </div>
      )}

      {/* Results */}
      {results && (
        <div className={styles.results}>
          <div className={styles.resultsHeader}>
            <h3 className={styles.resultsTitle}>Resultados</h3>
            <span className={styles.resultsBadge}>{successCount}/{results.length} OK</span>
          </div>

          <div className={styles.resultsTable}>
            <div className={styles.tableHeader}>
              <span>Archivo</span>
              <span>Comercio</span>
              <span>Fecha</span>
              <span>Fact. Simplif.</span>
              <span>Total</span>
              <span>Estado</span>
              <span></span>
            </div>
            {results.map((r, i) => (
              <div key={i} className={`${styles.tableRow} ${r.success ? '' : styles.tableRowError}`}>
                <span className={styles.cellFile}>{r.filename}</span>
                <span>{r.success ? r.data.vendor_name || '—' : '—'}</span>
                <span>{r.success ? r.data.date || '—' : '—'}</span>
                <span className={styles.cellMono}>{r.success ? r.data.simplified_invoice_number || '—' : '—'}</span>
                <span className={styles.cellMono}>{r.success ? `${(r.data.total ?? 0).toFixed(2)} €` : '—'}</span>
                <span>{r.success ? <span className={styles.statusOk}>✓</span> : <span className={styles.statusErr} title={r.error}>✗</span>}</span>
                <span>
                  {r.success && (
                    <button className={styles.dlBtn} onClick={() => downloadSingle(r, i)} title="Descargar PDF">⬇</button>
                  )}
                </span>
              </div>
            ))}
          </div>

          <div className={styles.actionsRow}>
            <button className={styles.ghostBtn} onClick={() => { setResults(null); setFiles([]) }}>
              Nuevo lote
            </button>
            {successCount > 0 && (
              <button className={styles.primaryBtn} onClick={downloadAll} disabled={generating}>
                {generating ? 'Generando...' : `⬇ Descargar ${successCount} facturas (ZIP)`}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Info card */}
      <div className={styles.infoCard}>
        <div className={styles.infoIcon}>ℹ️</div>
        <div>
          <strong>Declaración de la Renta - País Vasco</strong>
          <p className={styles.infoText}>
            Las facturas se generan con tus datos como destinatario (DNI: 78890774S) 
            y el supermercado como emisor. Incluyen nº de factura simplificada, base imponible e IVA.
          </p>
        </div>
      </div>
    </div>
  )
}
