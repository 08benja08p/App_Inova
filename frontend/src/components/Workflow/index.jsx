import { useCallback, useEffect, useRef, useState } from 'react';
import template from './Workflow.html?raw';
import './Workflow.css';
import {
  uploadDocument,
  getDocumentDetail,
  getDocumentEntities,
  getDocumentKeywords,
  getDocumentText,
} from '../../services/api';

const initialDocState = {
  docId: null,
  status: 'idle',
  statusMessage: 'Listo para cargar un archivo.',
  detail: null,
  textBlocks: [],
  entities: [],
  keywords: [],
  compliance: [],
  autoPlan: [],
  autoApplied: false,
  report: null,
  lastError: null,
  lastUpdatedAt: null,
};

export default function Workflow({ onReset }) {
  const containerRef = useRef(null);
  const elementsRef = useRef(null);
  const docStateRef = useRef(initialDocState);
  const mediaStreamRef = useRef(null);

  const [activeStep, setActiveStep] = useState('upload');
  const [docState, setDocState] = useState(initialDocState);

  const stopCameraStream = useCallback(() => {
    const stream = mediaStreamRef.current;
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    const elements = elementsRef.current;
    if (elements?.cameraVideo) {
      elements.cameraVideo.srcObject = null;
    }
    if (elements?.cameraPanel) {
      elements.cameraPanel.classList.remove('is-visible');
    }
  }, []);

  const loadDocumentData = useCallback(
    async (docId, { silent } = { silent: false }) => {
      if (!docId) {
        return;
      }
      setDocState((prev) => ({
        ...prev,
        status: silent ? prev.status : 'loading',
        statusMessage: silent ? prev.statusMessage : 'Sincronizando resultados...',
        lastError: null,
      }));
      try {
        const [detail, entities, keywords, textBlocks] = await Promise.all([
          getDocumentDetail(docId),
          getDocumentEntities(docId),
          getDocumentKeywords(docId),
          getDocumentText(docId),
        ]);
        const compliance = computeCompliance(detail, textBlocks, entities);
        setDocState((prev) => {
          const autoPlan = prev.autoApplied
            ? recomputeAutoPlan(prev.autoPlan, detail, entities, textBlocks)
            : prev.autoPlan;
          return {
            ...prev,
            docId,
            detail,
            entities,
            keywords,
            textBlocks,
            compliance,
            status: detail?.status ?? prev.status,
            statusMessage: 'Resultados listos.',
            lastUpdatedAt: new Date().toISOString(),
            lastError: null,
            autoApplied: prev.autoApplied ? prev.autoApplied : false,
            autoPlan,
            report: prev.autoApplied ? buildReport(detail, compliance, autoPlan) : prev.report,
          };
        });
      } catch (error) {
        setDocState((prev) => ({
          ...prev,
          status: 'error',
          statusMessage: 'Error al sincronizar datos.',
          lastError: error instanceof Error ? error.message : String(error),
        }));
      }
    },
    []
  );

  useEffect(() => {
    docStateRef.current = docState;
  }, [docState]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return undefined;
    }

    container.innerHTML = template;

    const elements = {
      stepButtons: container.querySelectorAll('[data-step-target]'),
      panels: container.querySelectorAll('[data-panel]'),
      uploadForm: container.querySelector('[data-form="upload"]'),
      uploadStatus: container.querySelector('[data-upload-status]'),
      statusBadge: container.querySelector('[data-doc-state-badge]'),
      docMeta: container.querySelector('[data-doc-meta]'),
      docSignals: container.querySelector('[data-doc-signals]'),
      textPreview: container.querySelector('[data-text-preview]'),
      keywordChips: container.querySelector('[data-keyword-chips]'),
      entityList: container.querySelector('[data-entity-list]'),
      autoOptions: container.querySelector('[data-auto-options]'),
      autoStatus: container.querySelector('[data-auto-status]'),
      autoResult: container.querySelector('[data-auto-result]'),
      summaryCard: container.querySelector('[data-summary-card]'),
      refreshButton: container.querySelector('[data-action="refresh-doc"]'),
      applyFixesButton: container.querySelector('[data-action="apply-fixes"]'),
      downloadButton: container.querySelector('[data-action="download-report"]'),
      logoutButton: container.querySelector('[data-action="logout"]'),
      openCameraButton: container.querySelector('[data-action="open-camera"]'),
      closeCameraButton: container.querySelector('[data-action="close-camera"]'),
      captureButton: container.querySelector('[data-action="capture-photo"]'),
      cameraPanel: container.querySelector('[data-camera-panel]'),
      cameraVideo: container.querySelector('[data-camera-video]'),
      cameraCanvas: container.querySelector('[data-camera-canvas]'),
    };

    elementsRef.current = elements;

    const handleStepClick = (event) => {
      const step = event.currentTarget.getAttribute('data-step-target');
      if (step) {
        setActiveStep(step);
      }
    };

    elements.stepButtons.forEach((button) => {
      button.addEventListener('click', handleStepClick);
    });

    const collectUploadOptions = () => {
      const docTypeSelect = elements.uploadForm?.querySelector('[name="doc_type"]');
      const languageSelect = elements.uploadForm?.querySelector('[name="language_hint"]');
      return {
        docType: docTypeSelect?.value?.toString() || undefined,
        languageHint: languageSelect?.value?.toString() || undefined,
      };
    };

    const submitDocument = async (file, options = {}) => {
      if (!(file instanceof File) || file.size === 0) {
        setDocState((prev) => ({
          ...prev,
          status: 'error',
          statusMessage: 'Selecciona un archivo válido.',
        }));
        return;
      }

      setDocState(() => ({
        ...initialDocState,
        status: 'uploading',
        statusMessage: 'Enviando documento...',
      }));
      setActiveStep('verify');

      try {
        const response = await uploadDocument(file, options);
        setDocState((prev) => ({
          ...prev,
          docId: response.id,
          status: response.status ?? 'processing',
          statusMessage: 'Documento recibido. Leyendo resultados...',
          detail: prev.detail,
        }));
        const fileInput = elements.uploadForm?.querySelector('input[type="file"]');
        if (fileInput) {
          fileInput.value = '';
        }
        await loadDocumentData(response.id, { silent: false });
      } catch (error) {
        setDocState((prev) => ({
          ...prev,
          status: 'error',
          statusMessage: 'No se pudo cargar el documento.',
          lastError: error instanceof Error ? error.message : String(error),
        }));
        setActiveStep('upload');
      }
    };

    const handleUpload = async (event) => {
      event.preventDefault();
      const form = elements.uploadForm;
      if (!form) {
        return;
      }
      const formData = new FormData(form);
      const file = formData.get('file');
      await submitDocument(file, {
        docType: (formData.get('doc_type') ?? '').toString() || undefined,
        languageHint: (formData.get('language_hint') ?? '').toString() || undefined,
      });
    };

    elements.uploadForm?.addEventListener('submit', handleUpload);

    const handleOpenCamera = async () => {
      if (!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)) {
        setDocState((prev) => ({
          ...prev,
          status: 'error',
          statusMessage: 'La cámara no está disponible en este dispositivo.',
          lastError: 'camera-not-supported',
        }));
        return;
      }

      try {
        stopCameraStream();
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: 'environment' } },
        });
        mediaStreamRef.current = stream;
        if (elements.cameraVideo) {
          elements.cameraVideo.srcObject = stream;
          await elements.cameraVideo.play().catch(() => {});
        }
        elements.cameraPanel?.classList.add('is-visible');
        setDocState((prev) => ({
          ...prev,
          status: 'capture',
          statusMessage: 'Cámara lista. Captura cuando estés listo.',
          lastError: null,
        }));
      } catch (error) {
        stopCameraStream();
        setDocState((prev) => ({
          ...prev,
          status: 'error',
          statusMessage: 'No pudimos acceder a la cámara.',
          lastError: error instanceof Error ? error.message : String(error),
        }));
      }
    };

    const handleCloseCamera = () => {
      stopCameraStream();
      setDocState((prev) => ({
        ...prev,
        status: prev.docId ? prev.status : 'idle',
        statusMessage: prev.docId ? prev.statusMessage : 'Listo para cargar un archivo.',
      }));
    };

    const handleCapture = async () => {
      const video = elements.cameraVideo;
      const canvas = elements.cameraCanvas;
      if (!video || !canvas) {
        return;
      }
      if (!video.videoWidth || !video.videoHeight) {
        setDocState((prev) => ({
          ...prev,
          status: 'error',
          statusMessage: 'La cámara aún no está lista.',
        }));
        return;
      }

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const context = canvas.getContext('2d');
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png', 0.92));
      if (!blob) {
        setDocState((prev) => ({
          ...prev,
          status: 'error',
          statusMessage: 'No se pudo generar la captura.',
          lastError: 'camera-capture-null',
        }));
        return;
      }

      setDocState((prev) => ({
        ...prev,
        status: 'uploading',
        statusMessage: 'Procesando captura...',
        lastError: null,
      }));

      const photoFile = new File([blob], `captura-${Date.now()}.png`, { type: 'image/png' });
      stopCameraStream();
      const options = collectUploadOptions();
      await submitDocument(photoFile, options);
    };

    elements.openCameraButton?.addEventListener('click', handleOpenCamera);
    elements.closeCameraButton?.addEventListener('click', handleCloseCamera);
    elements.captureButton?.addEventListener('click', handleCapture);

    const handleRefresh = () => {
      const currentId = docStateRef.current.docId;
      if (currentId) {
        loadDocumentData(currentId, { silent: false });
      }
    };

    elements.refreshButton?.addEventListener('click', handleRefresh);

    const handleApplyFixes = () => {
      const current = docStateRef.current;
      const optionsForm = elements.autoOptions;
      if (!optionsForm) {
        return;
      }
      if (!current.docId || !current.detail) {
        setDocState((prev) => ({
          ...prev,
          autoApplied: false,
          autoPlan: [],
          status: prev.status,
          statusMessage: 'Analiza el documento antes de generar ajustes.',
        }));
        setActiveStep('verify');
        return;
      }
      const selectedOptions = Array.from(optionsForm.querySelectorAll('input[type="checkbox"]'))
        .filter((input) => input.checked)
        .map((input) => input.name);
      const plan = buildAutoPlan(selectedOptions, current);
      setDocState((prev) => ({
        ...prev,
        autoApplied: true,
        autoPlan: plan,
        report: buildReport(prev.detail, prev.compliance, plan),
        statusMessage: prev.statusMessage,
      }));
      setActiveStep('summary');
    };

    elements.applyFixesButton?.addEventListener('click', handleApplyFixes);

    const handleDownload = () => {
      const current = docStateRef.current;
      if (!current.report) {
        return;
      }
      const blob = new Blob([JSON.stringify(current.report, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `inova-doc-${current.docId ?? 'sin-id'}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    };

    elements.downloadButton?.addEventListener('click', handleDownload);

    const handleLogout = (event) => {
      event.preventDefault();
      onReset();
    };

    elements.logoutButton?.addEventListener('click', handleLogout);

    renderStep(activeStep, elements);
    renderDocState(docStateRef.current, elements);

    return () => {
      elements.stepButtons.forEach((button) => {
        button.removeEventListener('click', handleStepClick);
      });
      elements.uploadForm?.removeEventListener('submit', handleUpload);
      elements.openCameraButton?.removeEventListener('click', handleOpenCamera);
      elements.closeCameraButton?.removeEventListener('click', handleCloseCamera);
      elements.captureButton?.removeEventListener('click', handleCapture);
      elements.refreshButton?.removeEventListener('click', handleRefresh);
      elements.applyFixesButton?.removeEventListener('click', handleApplyFixes);
      elements.downloadButton?.removeEventListener('click', handleDownload);
      elements.logoutButton?.removeEventListener('click', handleLogout);
      stopCameraStream();
    };
  }, [loadDocumentData, onReset, stopCameraStream]);

  useEffect(() => {
    const elements = elementsRef.current;
    if (!elements) {
      return;
    }
    renderStep(activeStep, elements);
  }, [activeStep]);

  useEffect(() => {
    const elements = elementsRef.current;
    if (!elements) {
      return;
    }
    renderDocState(docState, elements);
  }, [docState]);

  return <section className="workflow-host" ref={containerRef} />;
}

function renderStep(activeStep, elements) {
  elements.stepButtons.forEach((button) => {
    const step = button.getAttribute('data-step-target');
    if (step === activeStep) {
      button.classList.add('is-active');
    } else {
      button.classList.remove('is-active');
    }
  });

  elements.panels.forEach((panel) => {
    const panelKey = panel.getAttribute('data-panel');
    if (panelKey === activeStep) {
      panel.classList.add('is-active');
    } else {
      panel.classList.remove('is-active');
    }
  });
}

function renderDocState(state, elements) {
  if (!elements) {
    return;
  }

  if (elements.stepButtons) {
    elements.stepButtons.forEach((button) => {
      const step = button.getAttribute('data-step-target');
      const complete =
        (step === 'upload' && !!state.docId) ||
        (step === 'verify' && !!state.detail) ||
        (step === 'edit' && state.autoApplied) ||
        (step === 'summary' && state.report);
      if (complete) {
        button.classList.add('is-complete');
      } else {
        button.classList.remove('is-complete');
      }
    });
  }

  if (elements.uploadStatus) {
    elements.uploadStatus.textContent = state.statusMessage;
    elements.uploadStatus.setAttribute('data-status', state.status);
  }

  if (elements.statusBadge) {
    if (!state.docId) {
      elements.statusBadge.textContent = 'Sin documento cargado';
    } else if (state.status === 'error') {
      elements.statusBadge.textContent = 'Error en procesamiento';
    } else if (state.detail) {
      elements.statusBadge.textContent = `Documento ${state.detail.status ?? 'procesando'}`;
    } else {
      elements.statusBadge.textContent = 'Documento cargado';
    }
  }

  if (elements.docMeta) {
    elements.docMeta.innerHTML = '';
    if (!state.docId) {
      const item = document.createElement('li');
      item.textContent = 'Cargue un documento para ver metadatos.';
      elements.docMeta.appendChild(item);
    } else if (!state.detail) {
      const item = document.createElement('li');
      item.textContent = 'Sincronizando metadatos…';
      elements.docMeta.appendChild(item);
    } else {
      const { id, status, docType, languageDetected, createdAt, updatedAt } = state.detail;
      const metaEntries = [
        ['ID', id],
        ['Estado', status ?? 'sin estado'],
        ['Tipo', docType ?? 'No especificado'],
        ['Idioma detectado', languageDetected ?? 'No disponible'],
        ['Creado', formatDate(createdAt)],
        ['Actualizado', formatDate(updatedAt)],
      ];
      metaEntries.forEach(([label, value]) => {
        const item = document.createElement('li');
        const spanLabel = document.createElement('span');
        spanLabel.textContent = label;
        const spanValue = document.createElement('span');
        spanValue.textContent = value;
        item.append(spanLabel, spanValue);
        elements.docMeta.appendChild(item);
      });
    }
  }

  if (elements.docSignals) {
    elements.docSignals.innerHTML = '';
    if (!state.docId) {
      const item = document.createElement('li');
      item.textContent = 'Sin documento en proceso.';
      elements.docSignals.appendChild(item);
    } else if (!state.detail) {
      const item = document.createElement('li');
      item.textContent = 'Analizando requisitos…';
      elements.docSignals.appendChild(item);
    } else if (!state.compliance.length) {
      const item = document.createElement('li');
      item.setAttribute('data-severity', 'ok');
      const badge = document.createElement('span');
      badge.textContent = '✓ Cumple';
      item.append(badge, document.createTextNode(' No se detectaron incidencias.'));
      elements.docSignals.appendChild(item);
    } else {
      state.compliance.forEach((finding) => {
        const item = document.createElement('li');
        item.setAttribute('data-severity', finding.severity);
        const badge = document.createElement('span');
        badge.textContent = finding.title;
        item.append(badge, document.createTextNode(` ${finding.detail}`));
        elements.docSignals.appendChild(item);
      });
    }
  }

  if (elements.textPreview) {
    if (!state.docId) {
      elements.textPreview.textContent = 'Sube un documento para ver el texto reconocido.';
    } else {
      const text = state.textBlocks?.map((block) => block.text).join('\n\n').trim();
      elements.textPreview.textContent = text?.length ? text : 'Sin texto disponible.';
    }
  }

  if (elements.keywordChips) {
    elements.keywordChips.innerHTML = '';
    if (state.keywords?.length) {
      state.keywords.forEach((kw) => {
        const chip = document.createElement('span');
        chip.textContent = kw.keyword ?? '';
        elements.keywordChips.appendChild(chip);
      });
    } else if (state.docId) {
      const empty = document.createElement('span');
      empty.className = 'tag-cloud__empty';
      empty.textContent = 'Sin keywords detectadas.';
      elements.keywordChips.appendChild(empty);
    }
  }

  if (elements.entityList) {
    elements.entityList.innerHTML = '';
    if (state.entities?.length) {
      state.entities.forEach((entity) => {
        const item = document.createElement('li');
        const type = document.createElement('span');
        type.textContent = entity.type;
        const value = document.createElement('span');
        value.textContent = entity.value;
        const confidence = document.createElement('span');
        confidence.textContent = `${Math.round((entity.confidence ?? 0) * 100)}%`;
        item.append(type, value, confidence);
        elements.entityList.appendChild(item);
      });
    } else if (state.docId) {
      const item = document.createElement('li');
      item.className = 'entity-table__empty';
      item.textContent = 'Sin entidades extraídas.';
      elements.entityList.appendChild(item);
    }
  }

  if (elements.autoStatus) {
    if (!state.docId) {
      elements.autoStatus.textContent = 'Carga un documento antes de generar ajustes.';
    } else if (!state.autoApplied) {
      elements.autoStatus.textContent = 'Sin ajustes generados todavía.';
    } else {
      elements.autoStatus.textContent = 'Ajustes generados. Revisa el resumen antes de exportar.';
    }
  }

  if (elements.autoResult) {
    if (!state.autoApplied || !state.autoPlan.length) {
      elements.autoResult.innerHTML = '<p>Selecciona ajustes y presiona "Aplicar" para generar un plan.</p>';
    } else {
      const list = document.createElement('ul');
      state.autoPlan.forEach((item) => {
        const li = document.createElement('li');
        li.textContent = `${item.label}: ${item.detail}`;
        list.appendChild(li);
      });
      elements.autoResult.innerHTML = '';
      const intro = document.createElement('p');
      intro.textContent = 'Se generaron las siguientes modificaciones sugeridas:';
      elements.autoResult.append(intro, list);
    }
  }

  if (elements.summaryCard) {
    if (!state.docId || !state.detail) {
      elements.summaryCard.innerHTML = '<p>Necesitas procesar un documento para generar el resumen.</p>';
    } else {
      const summary = buildSummary(state);
      elements.summaryCard.innerHTML = '';
      const header = document.createElement('div');
      header.className = 'summary-head';
      const title = document.createElement('h3');
      title.textContent = `Documento ${state.detail.docType ?? 'sin tipo'}`;
      const badge = document.createElement('span');
      badge.textContent = state.detail.status ?? 'sin estado';
      header.append(title, badge);

      const meta = document.createElement('ul');
      meta.className = 'summary-meta';
      summary.meta.forEach(([label, value]) => {
        const item = document.createElement('li');
        const strong = document.createElement('strong');
        strong.textContent = label;
        const span = document.createElement('span');
        span.textContent = value;
        item.append(strong, span);
        meta.appendChild(item);
      });

      const findings = document.createElement('ul');
      findings.className = 'summary-findings';
      summary.findings.forEach((finding) => {
        const item = document.createElement('li');
        item.textContent = finding;
        findings.appendChild(item);
      });

      const adjustments = document.createElement('ul');
      adjustments.className = 'summary-adjustments';
      if (summary.adjustments.length) {
        summary.adjustments.forEach((adj) => {
          const li = document.createElement('li');
          li.textContent = adj;
          adjustments.appendChild(li);
        });
      }

      elements.summaryCard.append(header, meta);

      if (summary.textSummary) {
        const summaryTitle = document.createElement('h4');
        summaryTitle.textContent = 'Resumen del documento';
        const summaryBody = document.createElement('p');
        summaryBody.className = 'summary-text';
        summaryBody.textContent = summary.textSummary;
        elements.summaryCard.append(summaryTitle, summaryBody);
      }

      if (summary.textSnippet) {
        const textTitle = document.createElement('h4');
        textTitle.textContent = 'Texto reconocido';
        const textBody = document.createElement('p');
        textBody.className = 'summary-text';
        textBody.textContent = summary.textSnippet;
        elements.summaryCard.append(textTitle, textBody);
      }

      const keywordsTitle = document.createElement('h4');
      keywordsTitle.textContent = 'Palabras clave detectadas';
      if (summary.keywords.length) {
        const keywordList = document.createElement('ul');
        keywordList.className = 'summary-keywords';
        summary.keywords.forEach((kw) => {
          const item = document.createElement('li');
          const label = document.createElement('span');
          label.textContent = kw.keyword;
          item.appendChild(label);
          if (kw.score !== null) {
            const score = document.createElement('small');
            score.textContent = `${kw.score}%`;
            item.appendChild(score);
          }
          keywordList.appendChild(item);
        });
        elements.summaryCard.append(keywordsTitle, keywordList);
      } else {
        const noKeywords = document.createElement('p');
        noKeywords.className = 'summary-text summary-text--muted';
        noKeywords.textContent = 'Sin palabras clave detectadas.';
        elements.summaryCard.append(keywordsTitle, noKeywords);
      }

      if (summary.findings.length) {
        const findingsTitle = document.createElement('h4');
        findingsTitle.textContent = 'Hallazgos clave';
        elements.summaryCard.append(findingsTitle, findings);
      }
      if (summary.adjustments.length) {
        const adjustmentsTitle = document.createElement('h4');
        adjustmentsTitle.textContent = 'Acciones automáticas';
        elements.summaryCard.append(adjustmentsTitle, adjustments);
      }
    }
  }
}

function computeCompliance(detail, textBlocks, entities) {
  if (!detail) {
    return [];
  }
  const findings = [];
  const status = detail.status ?? 'processing';
  if (status !== 'done') {
    findings.push({
      severity: 'warning',
      title: 'Procesamiento incompleto',
      detail: 'El backend aún marca el documento como "' + status + '".',
    });
  }
  const text = textBlocks?.map((block) => block.text).join(' ').toLowerCase() ?? '';
  const entityTypes = new Set(entities?.map((entity) => entity.type) ?? []);
  const requiredEntities = [
    ['incoterm', 'INCOTERM faltante'],
    ['hs_code', 'HS Code no detectado'],
    ['bl_number', 'Número BL ausente'],
    ['container', 'Número de contenedor sin detectar'],
    ['amount', 'Monto sin identificar'],
  ];
  requiredEntities.forEach(([type, label]) => {
    if (!entityTypes.has(type)) {
      findings.push({
        severity: 'error',
        title: label,
        detail: 'Revisa el documento e ingresa el dato manualmente.',
      });
    }
  });
  if (entityTypes.has('incoterm') && !text.includes('fob')) {
    findings.push({
      severity: 'warning',
      title: 'INCOTERM inconsistente',
      detail: 'El texto OCR no menciona el INCOTERM detectado.',
    });
  }
  if (!detail.docType) {
    findings.push({
      severity: 'warning',
      title: 'Tipo de documento vacío',
      detail: 'Asigna un tipo para aplicar las reglas correctas.',
    });
  }
  return findings;
}

function buildAutoPlan(selectedOptions, state) {
  if (!state.docId) {
    return [];
  }
  const plan = [];
  if (selectedOptions.includes('normalize_amounts')) {
    plan.push({
      label: 'Normalización de montos',
      detail: 'Se convertirán todos los valores numéricos al formato 12345.67.',
    });
  }
  if (selectedOptions.includes('ensure_incoterm')) {
    const incoterm = state.entities.find((entity) => entity.type === 'incoterm');
    plan.push({
      label: 'Confirmación de INCOTERM',
      detail: incoterm
        ? `Se reforzará el INCOTERM ${incoterm.value} en cabecera y pie.`
        : 'Se solicitará ingresar el INCOTERM manualmente.',
    });
  }
  if (selectedOptions.includes('flag_missing_fields')) {
    const missing = ['container', 'bl_number', 'hs_code'].filter(
      (key) => !state.entities.some((entity) => entity.type === key)
    );
    plan.push({
      label: 'Campos obligatorios',
      detail: missing.length
        ? `Se marcarán como obligatorios: ${missing.join(', ')}.`
        : 'Todos los campos obligatorios están presentes.',
    });
  }
  if (selectedOptions.includes('language_consistency')) {
    plan.push({
      label: 'Unificación de idioma',
      detail: 'Las observaciones del informe se traducirán al español neutro.',
    });
  }
  return plan;
}

function recomputeAutoPlan(previousPlan, detail, entities, textBlocks) {
  if (!previousPlan?.length) {
    return previousPlan ?? [];
  }
  const mockState = {
    docId: detail?.id ?? null,
    entities: entities ?? [],
    textBlocks: textBlocks ?? [],
  };
  const selectedOptions = previousPlan.map((item) => {
    if (item.label.includes('montos')) {
      return 'normalize_amounts';
    }
    if (item.label.includes('INCOTERM')) {
      return 'ensure_incoterm';
    }
    if (item.label.includes('Campos')) {
      return 'flag_missing_fields';
    }
    if (item.label.includes('idioma')) {
      return 'language_consistency';
    }
    return null;
  }).filter(Boolean);
  return buildAutoPlan(selectedOptions, mockState);
}

function buildSummary(state) {
  const meta = [
    ['ID', state.detail?.id ?? 'N/D'],
    ['Estado', state.detail?.status ?? 'sin estado'],
    ['Tipo', state.detail?.docType ?? 'No definido'],
    ['Idioma detectado', state.detail?.languageDetected ?? 'No disponible'],
    ['Última actualización', formatDate(state.lastUpdatedAt ?? state.detail?.updatedAt)],
  ];
  const findings = state.compliance.length
    ? state.compliance.map((item) => `${item.title}: ${item.detail}`)
    : ['No se detectaron incidencias en las reglas evaluadas.'];
  const adjustments = state.autoApplied && state.autoPlan.length
    ? state.autoPlan.map((item) => `${item.label} → ${item.detail}`)
    : [];
  const rawKeywords = Array.isArray(state.keywords) ? state.keywords : [];
  const fullText = state.textBlocks
    ?.map((block) => block.text)
    .filter(Boolean)
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim();
  const textSummary = summarizeText(fullText, rawKeywords, {
    maxSentences: 3,
    maxLength: 520,
  });
  const keywords = rawKeywords
    .map((kw) => {
      const numericScore = Number(kw.score);
      return {
        keyword: kw.keyword ?? '',
        score: Number.isFinite(numericScore) ? Math.round(numericScore * 100) : null,
      };
    })
    .filter((kw) => kw.keyword.trim().length);
  let textSnippet = fullText ?? '';
  if (textSnippet.length > 420) {
    textSnippet = `${textSnippet.slice(0, 417).trimEnd()}…`;
  }
  return { meta, findings, adjustments, keywords, textSnippet, textSummary };
}

function summarizeText(text, keywords, { maxSentences = 3, maxLength = 480 } = {}) {
  if (!text) {
    return '';
  }
  const normalizedText = text.replace(/\s+/g, ' ').trim();
  if (!normalizedText) {
    return '';
  }
  const sentenceMatches = normalizedText.match(/[^.!?]+[.!?]?/gu);
  const sentences = (sentenceMatches ?? [normalizedText])
    .map((sentence) => sentence.trim())
    .filter(Boolean);
  if (!sentences.length) {
    return '';
  }
  if (sentences.length <= maxSentences) {
    return truncateSummary(sentences.join(' '), maxLength);
  }
  const keywordData = Array.isArray(keywords)
    ? keywords
        .map((item) => {
          const value = (item.keyword ?? item)?.toString().toLowerCase();
          const numericScore = Number(item.score);
          return {
            value,
            weight: Number.isFinite(numericScore) ? numericScore : 0.5,
          };
        })
        .filter((item) => item.value)
    : [];
  const scoredSentences = sentences.map((sentence, index) => {
    const normalizedSentence = sentence.toLowerCase();
    const keywordScore = keywordData.reduce((acc, keyword) => {
      return acc + (normalizedSentence.includes(keyword.value) ? 1 + keyword.weight : 0);
    }, 0);
    const lengthScore = Math.min(sentence.length / 180, 1);
    const positionScore = index === 0 ? 1 : 1 / (index + 1);
    return {
      sentence,
      index,
      score: keywordScore * 1.7 + lengthScore + positionScore,
    };
  });
  const topSentences = scoredSentences
    .sort((a, b) => b.score - a.score)
    .slice(0, maxSentences)
    .sort((a, b) => a.index - b.index)
    .map((item) => item.sentence.trim());
  return truncateSummary(topSentences.join(' '), maxLength);
}

function truncateSummary(text, maxLength) {
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, Math.max(0, maxLength - 1)).trimEnd()}…`;
}

function buildReport(detail, compliance, autoPlan) {
  if (!detail) {
    return null;
  }
  return {
    generatedAt: new Date().toISOString(),
    document: {
      id: detail.id,
      status: detail.status,
      type: detail.docType,
      languageDetected: detail.languageDetected,
      createdAt: detail.createdAt,
      updatedAt: detail.updatedAt,
    },
    compliance: compliance.map((item) => ({
      severity: item.severity,
      title: item.title,
      detail: item.detail,
    })),
    adjustments: autoPlan.map((item) => ({ label: item.label, detail: item.detail })),
  };
}

function formatDate(value) {
  if (!value) {
    return 'N/D';
  }
  try {
    return new Intl.DateTimeFormat('es', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(value));
  } catch (error) {
    return value.toString();
  }
}
