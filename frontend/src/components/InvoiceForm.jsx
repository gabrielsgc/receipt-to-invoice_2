import { useState } from 'react'
import { useForm, useFieldArray } from 'react-hook-form'
import toast from 'react-hot-toast'
import axios from 'axios'
import styles from './InvoiceForm.module.css'

function buildDefaultValues(receiptData) {
  const today = new Date().toISOString().split('T')[0]
  const due = new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0]
  const invoiceNum = `INV-${Date.now().toString().slice(-6)}`

  return {
    invoice_number: invoiceNum,
    date: today,
    due_date: due,
    currency: receiptData?.currency || 'USD',
    notes: receiptData?.notes || '',
    payment_terms: 'Net 30',
    issuer: {
      name: '',
      address: '',
      phone: '',
      email: '',
      tax_id: '',
    },
    client: {
      name: receiptData?.vendor_name || '',
      address: receiptData?.vendor_address || '',
      phone: receiptData?.vendor_phone || '',
      email: '',
      tax_id: '',
    },
    items: receiptData?.items?.length
      ? receiptData.items
      : [{ description: '', quantity: 1, unit_price: 0, total: 0 }],
    subtotal: receiptData?.subtotal ?? 0,
    tax_rate: 0,
    tax_amount: receiptData?.tax ?? 0,
    total: receiptData?.total ?? 0,
  }
}

function Field({ label, error, children }) {
  return (
    <div className={styles.field}>
      <label className={styles.label}>{label}</label>
      {children}
      {error && <span className={styles.error}>{error.message}</span>}
    </div>
  )
}

function PartySection({ title, icon, prefix, register, errors }) {
  const e = errors?.[prefix] || {}
  return (
    <div className={styles.section}>
      <h3 className={styles.sectionTitle}>
        <span className={styles.sectionIcon}>{icon}</span>
        {title}
      </h3>
      <div className={styles.grid2}>
        <Field label="Name *" error={e.name}>
          <input {...register(`${prefix}.name`, { required: 'Required' })} className={styles.input} placeholder="Company name" />
        </Field>
        <Field label="Email" error={e.email}>
          <input {...register(`${prefix}.email`)} type="email" className={styles.input} placeholder="email@company.com" />
        </Field>
        <Field label="Address" error={e.address}>
          <input {...register(`${prefix}.address`)} className={styles.input} placeholder="Street, City, Country" />
        </Field>
        <Field label="Phone" error={e.phone}>
          <input {...register(`${prefix}.phone`)} className={styles.input} placeholder="+1 555 000 0000" />
        </Field>
        <Field label="Tax ID" error={e.tax_id}>
          <input {...register(`${prefix}.tax_id`)} className={styles.input} placeholder="XX-XXXXXXX" />
        </Field>
      </div>
    </div>
  )
}

export default function InvoiceForm({ receiptData, onReset, onDownloaded }) {
  const [loading, setLoading] = useState(false)

  const {
    register,
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm({ defaultValues: buildDefaultValues(receiptData) })

  const { fields, append, remove } = useFieldArray({ control, name: 'items' })

  const items = watch('items')
  const taxRate = parseFloat(watch('tax_rate') || 0)

  function recalcTotals(newItems, rate) {
    const subtotal = newItems.reduce((sum, it) => sum + (parseFloat(it.total) || 0), 0)
    const taxAmount = subtotal * (rate / 100)
    setValue('subtotal', parseFloat(subtotal.toFixed(2)))
    setValue('tax_amount', parseFloat(taxAmount.toFixed(2)))
    setValue('total', parseFloat((subtotal + taxAmount).toFixed(2)))
  }

  function handleItemChange(index, field, value) {
    const updated = [...items]
    updated[index] = { ...updated[index], [field]: value }
    if (field === 'quantity' || field === 'unit_price') {
      const qty = parseFloat(updated[index].quantity) || 0
      const price = parseFloat(updated[index].unit_price) || 0
      updated[index].total = parseFloat((qty * price).toFixed(2))
      setValue(`items.${index}.total`, updated[index].total)
    }
    recalcTotals(updated, taxRate)
  }

  function handleTaxRateChange(e) {
    const rate = parseFloat(e.target.value) || 0
    recalcTotals(items, rate)
  }

  async function onSubmit(data) {
    setLoading(true)
    const toastId = toast.loading('Generating PDF…')
    try {
      const response = await axios.post('/api/invoices/generate', data, {
        responseType: 'blob',
      })
      const url = URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `invoice-${data.invoice_number}.pdf`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('Invoice downloaded!', { id: toastId })
      onDownloaded()
    } catch (err) {
      let msg = err.message
      if (err.response?.data instanceof Blob) {
        const text = await err.response.data.text()
        try { msg = JSON.parse(text).detail } catch {}
      }
      toast.error(`Error: ${msg}`, { id: toastId })
    } finally {
      setLoading(false)
    }
  }

  const subtotal = watch('subtotal')
  const taxAmount = watch('tax_amount')
  const total = watch('total')
  const currency = watch('currency') || 'USD'

  return (
    <form onSubmit={handleSubmit(onSubmit)} className={styles.form}>
      <div className={styles.formHeader}>
        <div className={styles.formHeaderLeft}>
          <button type="button" className={styles.backBtn} onClick={onReset}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="19" y1="12" x2="5" y2="12"/>
              <polyline points="12 19 5 12 12 5"/>
            </svg>
          </button>
          <div>
            <h1 className={styles.title}>Edit Invoice</h1>
            <p className={styles.titleHint}>Review and complete the extracted data</p>
          </div>
        </div>
        <button type="submit" className={styles.submitBtn} disabled={loading}>
          {loading ? (
            <span className={styles.submitLoading}>
              <span className={styles.submitSpinner} />
              Generating…
            </span>
          ) : (
            <>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              Export PDF
            </>
          )}
        </button>
      </div>

      {/* Invoice meta */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>
          <span className={styles.sectionIcon}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
              <line x1="16" y1="2" x2="16" y2="6"/>
              <line x1="8" y1="2" x2="8" y2="6"/>
              <line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
          </span>
          Invoice Details
        </h3>
        <div className={styles.grid3}>
          <Field label="Invoice No. *" error={errors.invoice_number}>
            <input {...register('invoice_number', { required: 'Required' })} className={`${styles.input} ${styles.monoInput}`} />
          </Field>
          <Field label="Date *" error={errors.date}>
            <input {...register('date', { required: 'Required' })} type="date" className={styles.input} />
          </Field>
          <Field label="Due Date">
            <input {...register('due_date')} type="date" className={styles.input} />
          </Field>
          <Field label="Currency">
            <select {...register('currency')} className={styles.input}>
              {['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'BRL', 'MXN'].map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </Field>
          <Field label="Payment Terms">
            <input {...register('payment_terms')} className={styles.input} />
          </Field>
        </div>
      </div>

      <div className={styles.partiesRow}>
        <PartySection title="From" icon="↑" prefix="issuer" register={register} errors={errors} />
        <PartySection title="Bill To" icon="↓" prefix="client" register={register} errors={errors} />
      </div>

      {/* Items */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>
          <span className={styles.sectionIcon}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="8" y1="6" x2="21" y2="6"/>
              <line x1="8" y1="12" x2="21" y2="12"/>
              <line x1="8" y1="18" x2="21" y2="18"/>
              <line x1="3" y1="6" x2="3.01" y2="6"/>
              <line x1="3" y1="12" x2="3.01" y2="12"/>
              <line x1="3" y1="18" x2="3.01" y2="18"/>
            </svg>
          </span>
          Line Items
        </h3>
        <div className={styles.itemsTable}>
          <div className={styles.itemsHeader}>
            <span>Description</span>
            <span>Qty</span>
            <span>Price</span>
            <span>Total</span>
            <span />
          </div>
          {fields.map((field, index) => (
            <div key={field.id} className={styles.itemRow}>
              <input
                {...register(`items.${index}.description`, { required: 'Required' })}
                className={styles.input}
                placeholder="Item description"
                onChange={(e) => handleItemChange(index, 'description', e.target.value)}
              />
              <input
                {...register(`items.${index}.quantity`)}
                type="number"
                min="0"
                step="any"
                className={`${styles.input} ${styles.monoInput}`}
                onChange={(e) => handleItemChange(index, 'quantity', e.target.value)}
              />
              <input
                {...register(`items.${index}.unit_price`)}
                type="number"
                min="0"
                step="any"
                className={`${styles.input} ${styles.monoInput}`}
                onChange={(e) => handleItemChange(index, 'unit_price', e.target.value)}
              />
              <input
                {...register(`items.${index}.total`)}
                type="number"
                step="any"
                className={`${styles.input} ${styles.monoInput} ${styles.totalInput}`}
                readOnly
              />
              <button
                type="button"
                className={styles.removeBtn}
                onClick={() => { remove(index); recalcTotals(items.filter((_, i) => i !== index), taxRate) }}
                title="Remove item"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
          ))}
          <button
            type="button"
            className={styles.addItemBtn}
            onClick={() => append({ description: '', quantity: 1, unit_price: 0, total: 0 })}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            Add line item
          </button>
        </div>
      </div>

      {/* Totals */}
      <div className={styles.bottomSection}>
        <div className={styles.bottomGrid}>
          <div className={styles.notesCol}>
            <Field label="Notes">
              <textarea {...register('notes')} className={styles.textarea} rows={4} placeholder="Additional notes, payment instructions…" />
            </Field>
          </div>
          <div className={styles.amountsCol}>
            <div className={styles.totalRow}>
              <span className={styles.totalLabel}>Subtotal</span>
              <span className={styles.totalValue}>{currency} {parseFloat(subtotal || 0).toFixed(2)}</span>
            </div>
            <div className={styles.totalRow}>
              <span className={styles.totalLabel}>
                Tax
                <input
                  {...register('tax_rate')}
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  className={styles.taxInput}
                  onChange={handleTaxRateChange}
                />
                <span className={styles.taxPercent}>%</span>
              </span>
              <span className={styles.totalValue}>{currency} {parseFloat(taxAmount || 0).toFixed(2)}</span>
            </div>
            <div className={`${styles.totalRow} ${styles.grandTotal}`}>
              <span className={styles.totalLabel}>Total</span>
              <span className={styles.totalValue}>{currency} {parseFloat(total || 0).toFixed(2)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile submit */}
      <div className={styles.mobileActions}>
        <button type="button" className={styles.ghostBtn} onClick={onReset}>Cancel</button>
        <button type="submit" className={styles.submitBtn} disabled={loading}>
          {loading ? 'Generating…' : 'Export PDF'}
        </button>
      </div>
    </form>
  )
}
