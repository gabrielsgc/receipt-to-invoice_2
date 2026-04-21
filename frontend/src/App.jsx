import { useState } from 'react'
import { Toaster } from 'react-hot-toast'
import UploadReceipt from './components/UploadReceipt'
import InvoiceForm from './components/InvoiceForm'
import styles from './App.module.css'

const STEPS = [
  { label: 'Upload', icon: '↑' },
  { label: 'Edit', icon: '✎' },
  { label: 'Export', icon: '↓' },
]

export default function App() {
  const [step, setStep] = useState(0)
  const [receiptData, setReceiptData] = useState(null)

  function handleReceiptExtracted(data) {
    setReceiptData(data)
    setStep(1)
  }

  function handleReset() {
    setReceiptData(null)
    setStep(0)
  }

  return (
    <div className={styles.app}>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#1C1C28',
            color: '#F0EDE6',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '10px',
            fontSize: '14px',
            fontFamily: 'Outfit, sans-serif',
          },
          success: { iconTheme: { primary: '#3DD68C', secondary: '#1C1C28' } },
          error: { iconTheme: { primary: '#F06060', secondary: '#1C1C28' } },
        }}
      />

      <header className={styles.header}>
        <div className={styles.headerInner}>
          <div className={styles.logoGroup}>
            <div className={styles.logoMark}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
              </svg>
            </div>
            <span className={styles.logoText}>receipt<span className={styles.logoAccent}>→</span>invoice</span>
          </div>

          <nav className={styles.steps}>
            {STEPS.map(({ label, icon }, i) => (
              <div key={label} className={styles.stepWrapper}>
                {i > 0 && <div className={`${styles.stepLine} ${i <= step ? styles.stepLineFilled : ''}`} />}
                <button
                  className={`${styles.step} ${i === step ? styles.stepActive : ''} ${i < step ? styles.stepDone : ''}`}
                  disabled
                >
                  <span className={styles.stepIcon}>{i < step ? '✓' : icon}</span>
                  <span className={styles.stepLabel}>{label}</span>
                </button>
              </div>
            ))}
          </nav>
        </div>
      </header>

      <main className={styles.main}>
        {step === 0 && (
          <div className={styles.fadeIn}>
            <UploadReceipt onExtracted={handleReceiptExtracted} />
          </div>
        )}
        {step >= 1 && receiptData && (
          <div className={styles.fadeIn}>
            <InvoiceForm
              receiptData={receiptData}
              onReset={handleReset}
              onDownloaded={() => setStep(2)}
            />
          </div>
        )}
        {step === 2 && (
          <div className={`${styles.doneCard} ${styles.fadeIn}`}>
            <div className={styles.doneGlow} />
            <div className={styles.doneIconWrap}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--success)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
            </div>
            <h2 className={styles.doneTitle}>Invoice exported</h2>
            <p className={styles.doneDesc}>Your PDF has been generated and downloaded successfully.</p>
            <button className={styles.primaryBtn} onClick={handleReset}>
              <span>Convert another receipt</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="23 4 23 10 17 10"/>
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
              </svg>
            </button>
          </div>
        )}
      </main>

      <footer className={styles.footer}>
        <span>Powered by GPT-4o Vision · Built with FastAPI & React</span>
      </footer>
    </div>
  )
}
