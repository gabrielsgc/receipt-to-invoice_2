import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import toast from 'react-hot-toast'
import axios from 'axios'
import PropTypes from 'prop-types'
import styles from './UploadReceipt.module.css'

const ACCEPTED = {
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
  'image/webp': ['.webp'],
  'application/pdf': ['.pdf'],
}

const FILE_TYPES = [
  { ext: 'JPG', color: '#D4A053' },
  { ext: 'PNG', color: '#3DD68C' },
  { ext: 'PDF', color: '#7C6BF0' },
  { ext: 'WebP', color: '#60A5FA' },
]

export default function UploadReceipt({ onExtracted }) {
  const [loading, setLoading] = useState(false)
  const [preview, setPreview] = useState(null)

  const onDrop = useCallback(
    async (acceptedFiles) => {
      const file = acceptedFiles[0]
      if (!file) return

      if (file.type.startsWith('image/')) {
        setPreview(URL.createObjectURL(file))
      } else {
        setPreview(null)
      }

      setLoading(true)
      const toastId = toast.loading('Analyzing receipt with GPT-4o…')

      try {
        const form = new FormData()
        form.append('file', file)
        const { data } = await axios.post('/api/receipts/analyze', form, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        toast.success('Receipt analyzed!', { id: toastId })
        onExtracted(data)
      } catch (err) {
        const msg = err.response?.data?.detail || err.message
        toast.error(`Error: ${msg}`, { id: toastId })
      } finally {
        setLoading(false)
      }
    },
    [onExtracted]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    maxFiles: 1,
    disabled: loading,
  })

  return (
    <div className={styles.wrapper}>
      <div className={styles.hero}>
        <span className={styles.badge}>AI-Powered</span>
        <h1 className={styles.title}>
          Transform receipts into
          <br />
          <span className={styles.titleAccent}>professional invoices</span>
        </h1>
        <p className={styles.subtitle}>
          Upload a receipt image or PDF — GPT-4o Vision extracts every detail automatically.
          Review, edit, and export as a polished invoice PDF.
        </p>
      </div>

      <div
        {...getRootProps()}
        className={`${styles.dropzone} ${isDragActive ? styles.active : ''} ${loading ? styles.disabled : ''}`}
      >
        <input {...getInputProps()} />

        <div className={styles.dropzoneInner}>
          {loading ? (
            <div className={styles.loadingState}>
              <div className={styles.spinnerTrack}>
                <div className={styles.spinner} />
              </div>
              <p className={styles.loadingText}>Extracting receipt data…</p>
              <p className={styles.loadingHint}>GPT-4o Vision is analyzing your receipt</p>
            </div>
          ) : (
            <>
              <div className={styles.uploadIcon}>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
              </div>
              <p className={styles.dropText}>
                {isDragActive ? 'Release to upload' : 'Drop a receipt here, or browse'}
              </p>
              <div className={styles.fileTypes}>
                {FILE_TYPES.map(({ ext, color }) => (
                  <span key={ext} className={styles.fileTag} style={{ '--tag-color': color }}>
                    {ext}
                  </span>
                ))}
                <span className={styles.sizeHint}>Max 10 MB</span>
              </div>
            </>
          )}
        </div>

        {/* Corner decorations */}
        <div className={`${styles.corner} ${styles.cornerTL}`} />
        <div className={`${styles.corner} ${styles.cornerTR}`} />
        <div className={`${styles.corner} ${styles.cornerBL}`} />
        <div className={`${styles.corner} ${styles.cornerBR}`} />
      </div>

      {preview && !loading && (
        <div className={styles.previewWrapper}>
          <div className={styles.previewHeader}>
            <span className={styles.previewLabel}>Preview</span>
            <span className={styles.previewDot} />
          </div>
          <img src={preview} alt="Receipt preview" className={styles.preview} />
        </div>
      )}

      <div className={styles.divider}>
        <span className={styles.dividerLine} />
        <span className={styles.dividerText}>or</span>
        <span className={styles.dividerLine} />
      </div>

      <button className={styles.manualBtn} onClick={() => onExtracted({})}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="12" y1="5" x2="12" y2="19"/>
          <line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        Enter data manually
      </button>
    </div>
  )
}

UploadReceipt.propTypes = {
  onExtracted: PropTypes.func.isRequired,
}
