(() => {
  const S = {
    uid: null,
    mid: 0,
    sid: 0,
    pc: null,
    making: false,
    polite: true,
    ignore: false,
    localScreenStream: null,
    screenSender: null,
    localRawAudioStream: null,
    localAudioStream: null,
    audioSender: null,
    localGainNode: null,
    localGateNode: null,
    localSpeechFocusGainNode: null,
    localSpeechDuckNode: null,
    localHighAnalyser: null,
    localHighAnalyserData: null,
    audioCtx: null,
    localAnalyser: null,
    localAnalyserData: null,
    localSourceNode: null,
    remoteAnalyser: null,
    remoteAnalyserData: null,
    remoteSourceNode: null,
    meterFrame: null,
    reconnectTimer: null,
    reconnecting: false,
    signalErrorCount: 0,
    streamQuality: 'medium',
    voiceConfig: {
      gain: 100,
      noiseSuppression: true,
      echoCancellation: true,
      autoGainControl: true,
      speechFocus: true,
      noiseGateEnabled: true,
      noiseGateThresholdDb: -34,
      noiseGateAttackMs: 7,
      noiseGateHoldMs: 120,
      noiseGateReleaseMs: 170,
      noiseGateRangeDb: -30,
      deviceId: ''
    },
    displayNames: { self: 'DatPixxel', partner: 'HawkEye' },
    roomTitle: 'Private Room',
    gateState: { env: 0, open: false, holdUntil: 0, gain: 0 },
    gateTestState: { env: 0, open: false, holdUntil: 0, gain: 0 },
    speechFocusState: { prevHigh: 0, duckHoldMs: 0, highGain: 1, duckGain: 1 },
    speechFocusTestState: { prevHigh: 0, duckHoldMs: 0, highGain: 1, duckGain: 1 },
    micTest: { running: false, stream: null, source: null, gainNode: null, gateNode: null, speechFocusGainNode: null, speechDuckNode: null, highAnalyser: null, highData: null, analyser: null, data: null, loopGain: null, recordDest: null, recorder: null, recordedBlobs: [], recMime: '' },
    voiceJoined: false,
    micMuted: false,
    partnerStreamOnline: false,
    partnerVoiceOnline: false,
    partnerMuted: false
  }

  const $ = (id) => document.getElementById(id)
  const E = {
    me: $('me-id'),
    partner: $('partner-state'),
    conn: $('connection-state'),
    localVideo: $('local-video'),
    remoteVideo: $('remote-video'),
    localState: $('local-state'),
    remoteState: $('remote-state'),
    chatLog: $('chat-log'),
    input: $('message-input'),
    streams: $('streams-area'),
    localCard: $('local-card'),
    remoteCard: $('remote-card'),
    voiceState: $('voice-state'),
    micState: $('mic-state'),
    partnerVoiceState: $('partner-voice-state'),
    selfVoiceBadge: $('self-voice-badge'),
    partnerVoiceBadge: $('partner-voice-badge'),
    selfNameLabel: $('self-name-label'),
    partnerNameLabel: $('partner-name-label'),
    roomTitleLabel: $('room-title-label'),
    selfMicIcon: $('self-mic-icon'),
    partnerMicIcon: $('partner-mic-icon'),
    selfLevelMarker: $('self-level-marker'),
    selfLevelFill: $('self-level-fill'),
    gateDebug: $('gate-debug'),
    menuSettings: $('menu-settings'),
    voiceSettingsPanel: $('voice-settings-panel'),
    micSettingsSubpanel: $('mic-settings-subpanel'),
    micGain: $('mic-gain'),
    micGainLabel: $('mic-gain-label'),
    selfDisplayName: $('self-display-name'),
    partnerDisplayName: $('partner-display-name'),
    roomTitleInput: $('room-title-input'),
    btnSwapNames: $('btn-swap-names'),
    micDeviceSelect: $('mic-device-select'),
    btnRefreshMics: $('btn-refresh-mics'),
    setGate: $('set-gate'),
    gatePreset: $('gate-preset'),
    gateThreshold: $('gate-threshold'),
    gateThresholdLabel: $('gate-threshold-label'),
    gateAttack: $('gate-attack'),
    gateAttackLabel: $('gate-attack-label'),
    gateHold: $('gate-hold'),
    gateHoldLabel: $('gate-hold-label'),
    gateRelease: $('gate-release'),
    gateReleaseLabel: $('gate-release-label'),
    gateRange: $('gate-range'),
    gateRangeLabel: $('gate-range-label'),
    btnMicTest: $('btn-mic-test'),
    micTestSaveMp3: $('mic-test-save-mp3'),
    micTestLoopback: $('mic-test-loopback'),
    micTestStatus: $('mic-test-status'),
    ampelRed: $('ampel-red'),
    ampelYellow: $('ampel-yellow'),
    ampelGreen: $('ampel-green'),
    setNoise: $('set-noise'),
    setEcho: $('set-echo'),
    setAgc: $('set-agc'),
    setSpeechFocus: $('set-speech-focus'),
    btnSend: $('btn-send'),
    streamQuality: $('stream-quality'),
    menuStream: $('menu-stream'),
    menuVoice: $('menu-voice'),
    btnMenuSettings: $('btn-menu-settings'),
    btnMicSettings: $('btn-mic-settings'),
    btnMenuStream: $('btn-menu-stream'),
    btnMenuVoice: $('btn-menu-voice'),
    btnSharePicker: $('btn-share-picker'),
    btnShareScreen: $('btn-share-screen'),
    btnShareWindow: $('btn-share-window'),
    btnStopShare: $('btn-stop-share-local'),
    localLiveDot: $('local-live-dot'),
    btnVoiceJoin: $('btn-voice-join'),
    btnMicToggle: $('btn-mic-toggle'),
    btnVoiceLeave: $('btn-voice-leave'),
    btnFullscreenLocal: $('btn-fullscreen-local'),
    btnFullscreenRemote: $('btn-fullscreen-remote'),
    btnOpenTs: $('btn-open-ts'),
    btnSourceLive: $('btn-source-live')
  }


  const QUALITY_PROFILES = {
    low: { label: 'Low', width: 960, height: 540, frameRate: 30 },
    medium: { label: 'Medium', width: 1280, height: 720, frameRate: 30 },
    high: { label: 'High', width: 1920, height: 1080, frameRate: 60 }
  }

  const GATE_PRESETS = {
    voice_soft: { thresholdDb: -45, attackMs: 12, holdMs: 220, releaseMs: 300, rangeDb: -12 },
    voice_strict: { thresholdDb: -34, attackMs: 7, holdMs: 120, releaseMs: 170, rangeDb: -30 },
    hard_gate: { thresholdDb: -24, attackMs: 2, holdMs: 40, releaseMs: 70, rangeDb: -50 }
  }

  const remoteAudio = document.createElement('audio')
  remoteAudio.autoplay = true
  remoteAudio.playsInline = true
  remoteAudio.style.display = 'none'
  document.body.appendChild(remoteAudio)

  const api = async (url, options = {}) => {
    const res = await fetch(url, {
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok || data.error) throw new Error(data.error || data.message || ('HTTP ' + res.status))
    return data
  }

  const setConn = (text, ok = false, bad = false) => {
    E.conn.textContent = text
    E.conn.className = 'status' + (ok ? ' ok' : '') + (bad ? ' bad' : '')
  }

  const setMeter = (el, value) => {
    if (!el) return
    const n = Math.max(0, Math.min(1, value || 0))
    el.style.width = Math.round(n * 100) + '%'
  }

  const setNodeGainSmooth = (node, target, timeConstant = 0.03) => {
    if (!node || !node.gain) return
    const t = Math.max(0, Math.min(1, target || 0))
    try {
      const now = S.audioCtx ? S.audioCtx.currentTime : 0
      node.gain.cancelScheduledValues(now)
      node.gain.setTargetAtTime(t, now, timeConstant)
    } catch (_) {
      node.gain.value = t
    }
  }

  const createAnalyser = (stream, side) => {
    if (!stream || !stream.getAudioTracks().length) return
    try {
      if (!S.audioCtx) S.audioCtx = new (window.AudioContext || window.webkitAudioContext)()
      if (S.audioCtx.state === 'suspended') S.audioCtx.resume().catch(() => {})

      const source = S.audioCtx.createMediaStreamSource(stream)
      const analyser = S.audioCtx.createAnalyser()
      analyser.fftSize = 256
      analyser.smoothingTimeConstant = 0.6
      source.connect(analyser)
      const data = new Uint8Array(analyser.fftSize)

      if (side === 'local') {
        if (S.localSourceNode) S.localSourceNode.disconnect()
        S.localSourceNode = source
        S.localAnalyser = analyser
        S.localAnalyserData = data
      } else {
        if (S.remoteSourceNode) S.remoteSourceNode.disconnect()
        S.remoteSourceNode = source
        S.remoteAnalyser = analyser
        S.remoteAnalyserData = data
      }
    } catch (_) {
    }
  }

  const clearAnalyser = (side) => {
    if (side === 'local') {
      if (S.localSourceNode) S.localSourceNode.disconnect()
      S.localSourceNode = null
      S.localAnalyser = null
      S.localAnalyserData = null
      S.localHighAnalyser = null
      S.localHighAnalyserData = null
      setMeter(E.selfLevelFill, 0)
      return
    }
    if (S.remoteSourceNode) S.remoteSourceNode.disconnect()
    S.remoteSourceNode = null
    S.remoteAnalyser = null
    S.remoteAnalyserData = null
  }

  const analyserRms = (analyser, data) => {
    if (!analyser || !data) return 0
    analyser.getByteTimeDomainData(data)
    let sum = 0
    for (let i = 0; i < data.length; i += 1) {
      const v = (data[i] - 128) / 128
      sum += v * v
    }
    return Math.min(1, Math.sqrt(sum / data.length))
  }

  const processSpeechFocusFrame = (state, speechLevel, highLevel, dtMs, enabled) => {
    if (!enabled) {
      state.prevHigh = highLevel
      state.duckHoldMs = 0
      state.highGain = 1
      state.duckGain = 1
      return { highGain: 1, duckGain: 1 }
    }

    const speechActive = speechLevel > 0.02
    const ratio = highLevel / Math.max(0.004, speechLevel)
    const transient = Math.max(0, highLevel - state.prevHigh)
    state.prevHigh = highLevel

    if (speechActive && (ratio > 1.55 || transient > 0.02)) {
      state.duckHoldMs = Math.max(state.duckHoldMs, 65)
    }
    state.duckHoldMs = Math.max(0, state.duckHoldMs - Math.max(1, dtMs))

    let highTarget = 1
    let duckTarget = 1
    if (speechActive) {
      if (ratio > 1.8 || transient > 0.03) {
        highTarget = 0.38
        duckTarget = state.duckHoldMs > 0 ? 0.72 : 0.86
      } else if (ratio > 1.55 || transient > 0.02) {
        highTarget = 0.55
        duckTarget = state.duckHoldMs > 0 ? 0.82 : 0.92
      }
    }

    const attackAlpha = 1 - Math.exp(-Math.max(1, dtMs) / 10)
    const releaseAlpha = 1 - Math.exp(-Math.max(1, dtMs) / 80)
    const highAlpha = highTarget < state.highGain ? attackAlpha : releaseAlpha
    const duckAlpha = duckTarget < state.duckGain ? attackAlpha : releaseAlpha
    state.highGain += (highTarget - state.highGain) * highAlpha
    state.duckGain += (duckTarget - state.duckGain) * duckAlpha

    return { highGain: state.highGain, duckGain: state.duckGain }
  }

  const smoothEnvelope = (prev, sample) => {
    if (sample > prev) return prev * 0.5 + sample * 0.5
    return prev * 0.8 + sample * 0.2
  }

  const dbToLin = (db) => Math.pow(10, db / 20)
  const linToDb = (lin) => 20 * Math.log10(Math.max(1e-6, lin))
  const thresholdDbToPercent = (db) => Math.max(0, Math.min(100, ((db + 60) / 50) * 100))

  const resetGateStates = () => {
    const closed = dbToLin(Number(S.voiceConfig.noiseGateRangeDb || -30))
    S.gateState = { env: 0, open: false, holdUntil: 0, gain: closed, timeMs: 0 }
    S.gateTestState = { env: 0, open: false, holdUntil: 0, gain: closed, timeMs: 0 }
    S.speechFocusState = { prevHigh: 0, duckHoldMs: 0, highGain: 1, duckGain: 1 }
    S.speechFocusTestState = { prevHigh: 0, duckHoldMs: 0, highGain: 1, duckGain: 1 }
  }

  const processGateFrame = (state, levelLin, dtMs, cfg) => {
    if (typeof state.timeMs !== 'number') state.timeMs = 0
    state.timeMs += Math.max(1, dtMs)
    state.env = smoothEnvelope(state.env, levelLin)
    const envDb = linToDb(state.env)

    const thresholdDb = Number(cfg.noiseGateThresholdDb)
    const attackMs = Math.max(1, Number(cfg.noiseGateAttackMs || 8))
    const holdMs = Math.max(0, Number(cfg.noiseGateHoldMs || 120))
    const releaseMs = Math.max(1, Number(cfg.noiseGateReleaseMs || 180))
    const rangeDb = Math.min(0, Number(cfg.noiseGateRangeDb || -30))
    const closedGain = dbToLin(rangeDb)

    const closeThresholdDb = thresholdDb - 2
    const above = envDb >= thresholdDb
    if (above) {
      state.holdUntil = state.timeMs + holdMs
      state.open = true
    } else if (state.timeMs > state.holdUntil && envDb < closeThresholdDb) {
      state.open = false
    }

    const target = state.open ? 1 : closedGain
    const tau = state.open ? attackMs : releaseMs
    const alpha = 1 - Math.exp(-Math.max(1, dtMs) / Math.max(1, tau))
    state.gain += (target - state.gain) * alpha

    return {
      gateOpen: state.open,
      gain: state.gain,
      envDb,
      thresholdDb,
      closedGain
    }
  }

  const meterLoop = () => {
    const local = analyserRms(S.localAnalyser, S.localAnalyserData)
    const localHigh = analyserRms(S.localHighAnalyser, S.localHighAnalyserData)
    let gatedLevel = 0
    let testGatedLevel = 0
    let gateDbg = 'Gate: idle'
    const dtMs = 16

    if (S.voiceJoined && S.localAudioStream) {
      const outTrack = S.localAudioStream.getAudioTracks()[0]
      if (outTrack) {
        const gate = processGateFrame(S.gateState, local, dtMs, S.voiceConfig)
        const gateEnabled = !!S.voiceConfig.noiseGateEnabled
        const gateOpen = gateEnabled ? gate.gateOpen : true
        const effectiveGain = gateEnabled ? gate.gain : 1
        const sf = processSpeechFocusFrame(S.speechFocusState, local, localHigh, dtMs, !!S.voiceConfig.speechFocus)
        outTrack.enabled = true
        setNodeGainSmooth(S.localSpeechFocusGainNode, sf.highGain, 0.02)
        setNodeGainSmooth(S.localSpeechDuckNode, sf.duckGain, 0.02)
        const gateGain = !S.micMuted ? effectiveGain : dbToLin(S.voiceConfig.noiseGateRangeDb)
        setNodeGainSmooth(S.localGateNode, gateGain, 0.02)
        gatedLevel = !S.micMuted
          ? (gateEnabled
            ? Math.max(0, (gate.envDb - gate.thresholdDb) / Math.max(1, 0 - gate.thresholdDb))
            : Math.min(1, local * 3.2))
          : 0
        gateDbg = `Live Gate: ${gateOpen ? 'open' : 'closed'} | env ${gate.envDb.toFixed(1)} dB | thr ${gate.thresholdDb.toFixed(1)} dB | gain ${(effectiveGain * 100).toFixed(0)}% | sfH ${(sf.highGain * 100).toFixed(0)}% | sfD ${(sf.duckGain * 100).toFixed(0)}%`
      }
    }

    if (S.micTest.running && S.micTest.analyser && S.micTest.data) {
      const t = analyserRms(S.micTest.analyser, S.micTest.data)
      const tHigh = analyserRms(S.micTest.highAnalyser, S.micTest.highData)
      setAmpelState(t)
      const gate = processGateFrame(S.gateTestState, t, dtMs, S.voiceConfig)
      const gateEnabled = !!S.voiceConfig.noiseGateEnabled
      const effectiveGain = gateEnabled ? gate.gain : 1
      const sf = processSpeechFocusFrame(S.speechFocusTestState, t, tHigh, dtMs, !!S.voiceConfig.speechFocus)
      setNodeGainSmooth(S.micTest.speechFocusGainNode, sf.highGain, 0.02)
      setNodeGainSmooth(S.micTest.speechDuckNode, sf.duckGain, 0.02)
      setNodeGainSmooth(S.micTest.gateNode, effectiveGain, 0.02)
      if (S.micTest.loopGain) {
        setNodeGainSmooth(S.micTest.loopGain, 0.18 * effectiveGain, 0.02)
      }
      testGatedLevel = gateEnabled
        ? (gate.gateOpen ? Math.max(0, (gate.envDb - gate.thresholdDb) / Math.max(1, 0 - gate.thresholdDb)) : 0)
        : Math.min(1, t * 3.2)
      gateDbg = `Test Gate: ${(gateEnabled ? (gate.gateOpen ? 'open' : 'closed') : 'off')} | env ${gate.envDb.toFixed(1)} dB | thr ${gate.thresholdDb.toFixed(1)} dB | gain ${(effectiveGain * 100).toFixed(0)}% | sfH ${(sf.highGain * 100).toFixed(0)}% | sfD ${(sf.duckGain * 100).toFixed(0)}%`
    }

    setMeter(E.selfLevelFill, S.voiceJoined ? gatedLevel : testGatedLevel)
    if (E.gateDebug) E.gateDebug.textContent = gateDbg

    S.meterFrame = window.requestAnimationFrame(meterLoop)
  }

  const ensureMeterLoop = () => {
    if (S.meterFrame) return
    S.meterFrame = window.requestAnimationFrame(meterLoop)
  }

  const syncVoiceConfigFromUi = () => {
    if (E.micGain) S.voiceConfig.gain = Number(E.micGain.value || 100)
    if (E.micDeviceSelect) S.voiceConfig.deviceId = E.micDeviceSelect.value || ''
    if (E.setNoise) S.voiceConfig.noiseSuppression = !!E.setNoise.checked
    if (E.setEcho) S.voiceConfig.echoCancellation = !!E.setEcho.checked
    if (E.setAgc) S.voiceConfig.autoGainControl = !!E.setAgc.checked
    if (E.setSpeechFocus) S.voiceConfig.speechFocus = !!E.setSpeechFocus.checked
    if (E.setGate) S.voiceConfig.noiseGateEnabled = !!E.setGate.checked
    if (E.gateThreshold) S.voiceConfig.noiseGateThresholdDb = Number(E.gateThreshold.value || -34)
    if (E.gateAttack) S.voiceConfig.noiseGateAttackMs = Number(E.gateAttack.value || 7)
    if (E.gateHold) S.voiceConfig.noiseGateHoldMs = Number(E.gateHold.value || 120)
    if (E.gateRelease) S.voiceConfig.noiseGateReleaseMs = Number(E.gateRelease.value || 170)
    if (E.gateRange) S.voiceConfig.noiseGateRangeDb = Number(E.gateRange.value || -30)
    if (E.micGainLabel) E.micGainLabel.textContent = `${S.voiceConfig.gain}%`
    if (E.gateThresholdLabel) E.gateThresholdLabel.textContent = `${Math.round(S.voiceConfig.noiseGateThresholdDb)} dB`
    if (E.gateAttackLabel) E.gateAttackLabel.textContent = `${Math.round(S.voiceConfig.noiseGateAttackMs)} ms`
    if (E.gateHoldLabel) E.gateHoldLabel.textContent = `${Math.round(S.voiceConfig.noiseGateHoldMs)} ms`
    if (E.gateReleaseLabel) E.gateReleaseLabel.textContent = `${Math.round(S.voiceConfig.noiseGateReleaseMs)} ms`
    if (E.gateRangeLabel) E.gateRangeLabel.textContent = `${Math.round(S.voiceConfig.noiseGateRangeDb)} dB`
    if (E.selfLevelMarker) E.selfLevelMarker.style.left = `${thresholdDbToPercent(S.voiceConfig.noiseGateThresholdDb)}%`
    if (S.localGainNode) S.localGainNode.gain.value = S.voiceConfig.gain / 100
    if (S.micTest.gainNode) S.micTest.gainNode.gain.value = S.voiceConfig.gain / 100
    if (!S.voiceConfig.speechFocus) {
      if (S.localSpeechFocusGainNode) S.localSpeechFocusGainNode.gain.value = 1
      if (S.localSpeechDuckNode) S.localSpeechDuckNode.gain.value = 1
      if (S.micTest.speechFocusGainNode) S.micTest.speechFocusGainNode.gain.value = 1
      if (S.micTest.speechDuckNode) S.micTest.speechDuckNode.gain.value = 1
    }
  }

  const setGatePresetCustomIfNeeded = () => {
    if (!E.gatePreset) return
    const current = E.gatePreset.value || 'custom'
    if (current !== 'custom') E.gatePreset.value = 'custom'
  }

  const applyDisplayNames = () => {
    const selfName = (S.displayNames.self || 'Du').trim() || 'Du'
    const partnerName = (S.displayNames.partner || 'Partner').trim() || 'Partner'
    if (E.selfNameLabel) E.selfNameLabel.textContent = selfName
    if (E.partnerNameLabel) E.partnerNameLabel.textContent = partnerName
    if (E.selfDisplayName) E.selfDisplayName.value = selfName
    if (E.partnerDisplayName) E.partnerDisplayName.value = partnerName
  }

  const applyRoomTitle = () => {
    const title = (S.roomTitle || 'Private Room').trim() || 'Private Room'
    if (E.roomTitleLabel) E.roomTitleLabel.textContent = title
    if (E.roomTitleInput) E.roomTitleInput.value = title
  }

  const syncDisplayNamesFromUi = () => {
    if (E.selfDisplayName) S.displayNames.self = (E.selfDisplayName.value || '').trim() || 'Du'
    if (E.partnerDisplayName) S.displayNames.partner = (E.partnerDisplayName.value || '').trim() || 'Partner'
    window.localStorage.setItem('chat_display_name_self', S.displayNames.self)
    window.localStorage.setItem('chat_display_name_partner', S.displayNames.partner)
    applyDisplayNames()
  }

  const syncRoomTitleFromUi = () => {
    if (E.roomTitleInput) S.roomTitle = (E.roomTitleInput.value || '').trim() || 'Private Room'
    window.localStorage.setItem('chat_room_title', S.roomTitle)
    applyRoomTitle()
  }

  const setGateUiFromConfig = () => {
    if (E.gateThreshold) E.gateThreshold.value = String(S.voiceConfig.noiseGateThresholdDb)
    if (E.gateAttack) E.gateAttack.value = String(S.voiceConfig.noiseGateAttackMs)
    if (E.gateHold) E.gateHold.value = String(S.voiceConfig.noiseGateHoldMs)
    if (E.gateRelease) E.gateRelease.value = String(S.voiceConfig.noiseGateReleaseMs)
    if (E.gateRange) E.gateRange.value = String(S.voiceConfig.noiseGateRangeDb)
    syncVoiceConfigFromUi()
    resetGateStates()
  }

  const applyGatePreset = (presetKey) => {
    const p = GATE_PRESETS[presetKey]
    if (!p) return
    S.voiceConfig.noiseGateThresholdDb = p.thresholdDb
    S.voiceConfig.noiseGateAttackMs = p.attackMs
    S.voiceConfig.noiseGateHoldMs = p.holdMs
    S.voiceConfig.noiseGateReleaseMs = p.releaseMs
    S.voiceConfig.noiseGateRangeDb = p.rangeDb
    if (E.gatePreset) E.gatePreset.value = presetKey
    setGateUiFromConfig()
  }

  const loadDisplayNames = () => {
    const selfSaved = window.localStorage.getItem('chat_display_name_self')
    const partnerSaved = window.localStorage.getItem('chat_display_name_partner')
    if (selfSaved && selfSaved.trim()) S.displayNames.self = selfSaved.trim()
    if (partnerSaved && partnerSaved.trim()) S.displayNames.partner = partnerSaved.trim()
    applyDisplayNames()
  }

  const loadRoomTitle = () => {
    const saved = window.localStorage.getItem('chat_room_title')
    if (saved && saved.trim()) S.roomTitle = saved.trim()
    applyRoomTitle()
  }

  const swapDisplayNames = () => {
    const a = S.displayNames.self
    S.displayNames.self = S.displayNames.partner || 'Partner'
    S.displayNames.partner = a || 'Du'
    window.localStorage.setItem('chat_display_name_self', S.displayNames.self)
    window.localStorage.setItem('chat_display_name_partner', S.displayNames.partner)
    applyDisplayNames()
  }

  const getLocalVoiceConstraints = () => ({
    ...(S.voiceConfig.deviceId ? { deviceId: { exact: S.voiceConfig.deviceId } } : {}),
    echoCancellation: S.voiceConfig.echoCancellation,
    noiseSuppression: S.voiceConfig.noiseSuppression,
    autoGainControl: S.voiceConfig.autoGainControl,
    channelCount: 1,
    advanced: S.voiceConfig.speechFocus ? [
      { googTypingNoiseDetection: true },
      { googNoiseSuppression: true },
      { googNoiseSuppression2: true },
      { googHighpassFilter: true }
    ] : []
  })

  const getTrackProcessingConstraints = () => ({
    echoCancellation: S.voiceConfig.echoCancellation,
    noiseSuppression: S.voiceConfig.noiseSuppression,
    autoGainControl: S.voiceConfig.autoGainControl,
    advanced: S.voiceConfig.speechFocus ? [
      { googTypingNoiseDetection: true },
      { googNoiseSuppression: true },
      { googNoiseSuppression2: true },
      { googHighpassFilter: true }
    ] : []
  })

  const tryApplyTrackProcessingConstraints = async (stream) => {
    const track = stream && stream.getAudioTracks ? stream.getAudioTracks()[0] : null
    if (!track || typeof track.applyConstraints !== 'function') return false
    try {
      await track.applyConstraints(getTrackProcessingConstraints())
      return true
    } catch (_) {
      return false
    }
  }

  const getTrackDeviceId = (stream) => {
    const track = stream && stream.getAudioTracks ? stream.getAudioTracks()[0] : null
    if (!track || typeof track.getSettings !== 'function') return ''
    const settings = track.getSettings() || {}
    return settings.deviceId || ''
  }

  const setAmpelState = (level) => {
    if (!E.ampelRed || !E.ampelYellow || !E.ampelGreen) return
    E.ampelRed.classList.remove('on-red')
    E.ampelYellow.classList.remove('on-yellow')
    E.ampelGreen.classList.remove('on-green')
    if (level < 0.01) E.ampelRed.classList.add('on-red')
    else if (level < 0.03) E.ampelYellow.classList.add('on-yellow')
    else E.ampelGreen.classList.add('on-green')
  }

  const mergeFloat32Chunks = (chunks) => {
    const total = chunks.reduce((n, c) => n + c.length, 0)
    const out = new Float32Array(total)
    let offset = 0
    chunks.forEach((c) => {
      out.set(c, offset)
      offset += c.length
    })
    return out
  }

  const floatToInt16 = (input) => {
    const out = new Int16Array(input.length)
    for (let i = 0; i < input.length; i += 1) {
      const s = Math.max(-1, Math.min(1, input[i]))
      out[i] = s < 0 ? s * 0x8000 : s * 0x7fff
    }
    return out
  }

  const encodeMp3Blob = (floatSamples, sampleRate) => {
    if (!window.lamejs) throw new Error('MP3 Encoder nicht geladen')
    const pcm = floatToInt16(floatSamples)
    const encoder = new window.lamejs.Mp3Encoder(1, sampleRate, 128)
    const block = 1152
    const parts = []
    for (let i = 0; i < pcm.length; i += block) {
      const chunk = pcm.subarray(i, i + block)
      const buf = encoder.encodeBuffer(chunk)
      if (buf.length) parts.push(new Int8Array(buf))
    }
    const end = encoder.flush()
    if (end.length) parts.push(new Int8Array(end))
    return new Blob(parts, { type: 'audio/mpeg' })
  }

  const saveBlobAsMp3 = async (blob) => {
    const fileName = `mic-test-${new Date().toISOString().replace(/[:.]/g, '-')}.mp3`
    if (window.showSaveFilePicker) {
      const handle = await window.showSaveFilePicker({
        suggestedName: fileName,
        types: [{ description: 'MP3 Audio', accept: { 'audio/mpeg': ['.mp3'] } }]
      })
      const writable = await handle.createWritable()
      await writable.write(blob)
      await writable.close()
      return
    }
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = fileName
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }


  const stopMicTest = async (saveIfRequested = false) => {
    let recordedBlobs = S.micTest.recordedBlobs ? [...S.micTest.recordedBlobs] : []

    if (S.micTest.recorder && S.micTest.recorder.state !== 'inactive') {
      await new Promise((resolve) => {
        let done = false
        const finish = () => {
          if (done) return
          done = true
          resolve()
        }
        S.micTest.recorder.onstop = () => finish()
        try {
          S.micTest.recorder.stop()
        } catch (_) {
          finish()
        }
        window.setTimeout(finish, 1600)
      })
      recordedBlobs = S.micTest.recordedBlobs ? [...S.micTest.recordedBlobs] : recordedBlobs
    }

    S.micTest.recorder = null
    if (S.micTest.recordDest) {
      try { S.micTest.recordDest.disconnect() } catch (_) {}
      S.micTest.recordDest = null
    }
    if (S.micTest.loopGain) {
      try { S.micTest.loopGain.disconnect() } catch (_) {}
      S.micTest.loopGain = null
    }
    if (S.micTest.source) {
      try { S.micTest.source.disconnect() } catch (_) {}
      S.micTest.source = null
    }
    if (S.micTest.gainNode) {
      try { S.micTest.gainNode.disconnect() } catch (_) {}
      S.micTest.gainNode = null
    }
    if (S.micTest.speechFocusGainNode) {
      try { S.micTest.speechFocusGainNode.disconnect() } catch (_) {}
      S.micTest.speechFocusGainNode = null
    }
    if (S.micTest.speechDuckNode) {
      try { S.micTest.speechDuckNode.disconnect() } catch (_) {}
      S.micTest.speechDuckNode = null
    }
    if (S.micTest.gateNode) {
      try { S.micTest.gateNode.disconnect() } catch (_) {}
      S.micTest.gateNode = null
    }
    if (S.micTest.stream) {
      S.micTest.stream.getTracks().forEach((t) => t.stop())
      S.micTest.stream = null
    }
    S.micTest.analyser = null
    S.micTest.data = null
    S.micTest.highAnalyser = null
    S.micTest.highData = null
    S.micTest.recordedBlobs = []
    S.micTest.recMime = ''
    S.micTest.running = false
    resetGateStates()
    if (E.btnMicTest) E.btnMicTest.textContent = 'Mikrofon-Test starten'
    if (E.micTestStatus) E.micTestStatus.textContent = 'Mic-Test: aus'
    setAmpelState(0)

    if (saveIfRequested && E.micTestSaveMp3 && E.micTestSaveMp3.checked && recordedBlobs.length > 0) {
      try {
        const webBlob = new Blob(recordedBlobs, { type: S.micTest.recMime || 'audio/webm' })
        const arr = await webBlob.arrayBuffer()
        const decodeCtx = S.audioCtx || new (window.AudioContext || window.webkitAudioContext)()
        const decoded = await decodeCtx.decodeAudioData(arr.slice(0))
        const ch0 = decoded.getChannelData(0)
        const mp3Blob = encodeMp3Blob(new Float32Array(ch0), Math.round(decoded.sampleRate || 48000))
        await saveBlobAsMp3(mp3Blob)
      } catch (e) {
        if (E.micTestStatus) E.micTestStatus.textContent = `Mic-Test Save Fehler: ${e.message}`
      }
    }
  }

  const startMicTest = async () => {
    syncVoiceConfigFromUi()
    if (!S.audioCtx) S.audioCtx = new (window.AudioContext || window.webkitAudioContext)()
    if (S.audioCtx.state === 'suspended') await S.audioCtx.resume().catch(() => {})

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: getLocalVoiceConstraints(),
      video: false
    })

    const source = S.audioCtx.createMediaStreamSource(stream)
    const gainNode = S.audioCtx.createGain()
    gainNode.gain.value = S.voiceConfig.gain / 100
    const lowPass = S.audioCtx.createBiquadFilter()
    lowPass.type = 'lowpass'
    lowPass.frequency.value = 3600
    lowPass.Q.value = 0.5
    const highPass = S.audioCtx.createBiquadFilter()
    highPass.type = 'highpass'
    highPass.frequency.value = 3600
    highPass.Q.value = 0.5
    const speechFocusGainNode = S.audioCtx.createGain()
    speechFocusGainNode.gain.value = 1
    const speechDuckNode = S.audioCtx.createGain()
    speechDuckNode.gain.value = 1
    const gateNode = S.audioCtx.createGain()
    gateNode.gain.value = 1
    const analyser = S.audioCtx.createAnalyser()
    analyser.fftSize = 256
    analyser.smoothingTimeConstant = 0.6
    const highAnalyser = S.audioCtx.createAnalyser()
    highAnalyser.fftSize = 256
    highAnalyser.smoothingTimeConstant = 0.45
    source.connect(gainNode)
    gainNode.connect(analyser)
    gainNode.connect(lowPass)
    gainNode.connect(highPass)
    highPass.connect(highAnalyser)
    highPass.connect(speechFocusGainNode)
    speechFocusGainNode.connect(speechDuckNode)
    lowPass.connect(speechDuckNode)
    speechDuckNode.connect(gateNode)

    const recordDest = S.audioCtx.createMediaStreamDestination()
    // Record post-gate signal so Noise Gate changes are audible in file.
    gateNode.connect(recordDest)

    if (!window.MediaRecorder) {
      throw new Error('MediaRecorder wird vom Browser nicht unterstützt')
    }

    const mimeCandidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus']
    let recMime = ''
    for (const m of mimeCandidates) {
      if (window.MediaRecorder.isTypeSupported && window.MediaRecorder.isTypeSupported(m)) {
        recMime = m
        break
      }
    }

    const recorder = recMime ? new window.MediaRecorder(recordDest.stream, { mimeType: recMime }) : new window.MediaRecorder(recordDest.stream)
    const recordedBlobs = []
    recorder.ondataavailable = (evt) => {
      if (evt.data && evt.data.size > 0) recordedBlobs.push(evt.data)
    }
    recorder.start(250)

    let loopGain = null
    if (E.micTestLoopback && E.micTestLoopback.checked) {
      loopGain = S.audioCtx.createGain()
      loopGain.gain.value = 0.18
      gateNode.connect(loopGain)
      loopGain.connect(S.audioCtx.destination)
    }

    S.micTest.running = true
    S.micTest.stream = stream
    S.micTest.source = source
    S.micTest.gainNode = gainNode
    S.micTest.speechFocusGainNode = speechFocusGainNode
    S.micTest.speechDuckNode = speechDuckNode
    S.micTest.gateNode = gateNode
    S.micTest.recordDest = recordDest
    S.micTest.recorder = recorder
    S.micTest.recordedBlobs = recordedBlobs
    S.micTest.recMime = recMime
    S.micTest.analyser = analyser
    S.micTest.data = new Uint8Array(analyser.fftSize)
    S.micTest.highAnalyser = highAnalyser
    S.micTest.highData = new Uint8Array(highAnalyser.fftSize)
    S.micTest.loopGain = loopGain
    resetGateStates()
    ensureMeterLoop()
    if (E.btnMicTest) E.btnMicTest.textContent = 'Mikrofon-Test stoppen'
    if (E.micTestStatus) E.micTestStatus.textContent = E.micTestLoopback && E.micTestLoopback.checked ? 'Mic-Test: aktiv (Loopback, MP3 mit Gate)' : 'Mic-Test: aktiv (MP3 mit Gate)'
  }

  const getQualityProfile = () => {
    const key = S.streamQuality in QUALITY_PROFILES ? S.streamQuality : 'medium'
    return QUALITY_PROFILES[key]
  }

  const getDisplayVideoConstraints = (mode) => {
    const q = getQualityProfile()
    const base = {
      frameRate: { ideal: q.frameRate, max: q.frameRate },
      width: { ideal: q.width },
      height: { ideal: q.height }
    }
    if (mode === 'screen') return { ...base, displaySurface: 'monitor' }
    if (mode === 'window') return { ...base, displaySurface: 'window' }
    return base
  }

  const applyQualityToActiveShare = async () => {
    if (!S.localScreenStream) return
    const track = S.localScreenStream.getVideoTracks()[0]
    if (!track || typeof track.applyConstraints !== 'function') return
    const q = getQualityProfile()
    try {
      await track.applyConstraints({
        frameRate: q.frameRate,
        width: q.width,
        height: q.height
      })
      E.localState.textContent = `live (${q.label})`
    } catch (_) {
      // Some browsers/OS capture paths reject runtime changes.
    }
  }

  const buildLocalVoiceStream = (rawStream) => {
    if (!S.audioCtx) S.audioCtx = new (window.AudioContext || window.webkitAudioContext)()
    if (S.audioCtx.state === 'suspended') S.audioCtx.resume().catch(() => {})

    const source = S.audioCtx.createMediaStreamSource(rawStream)
    const gainNode = S.audioCtx.createGain()
    gainNode.gain.value = S.voiceConfig.gain / 100
    const lowPass = S.audioCtx.createBiquadFilter()
    lowPass.type = 'lowpass'
    lowPass.frequency.value = 3600
    lowPass.Q.value = 0.5
    const highPass = S.audioCtx.createBiquadFilter()
    highPass.type = 'highpass'
    highPass.frequency.value = 3600
    highPass.Q.value = 0.5
    const speechFocusGainNode = S.audioCtx.createGain()
    speechFocusGainNode.gain.value = 1
    const speechDuckNode = S.audioCtx.createGain()
    speechDuckNode.gain.value = 1
    const gateNode = S.audioCtx.createGain()
    gateNode.gain.value = 1
    const analyser = S.audioCtx.createAnalyser()
    analyser.fftSize = 256
    analyser.smoothingTimeConstant = 0.6
    const highAnalyser = S.audioCtx.createAnalyser()
    highAnalyser.fftSize = 256
    highAnalyser.smoothingTimeConstant = 0.45
    const data = new Uint8Array(analyser.fftSize)
    const highData = new Uint8Array(highAnalyser.fftSize)
    const destination = S.audioCtx.createMediaStreamDestination()

    source.connect(gainNode)
    gainNode.connect(analyser)
    gainNode.connect(lowPass)
    gainNode.connect(highPass)
    highPass.connect(highAnalyser)
    highPass.connect(speechFocusGainNode)
    speechFocusGainNode.connect(speechDuckNode)
    lowPass.connect(speechDuckNode)
    speechDuckNode.connect(gateNode)
    gateNode.connect(destination)

    if (S.localSourceNode) S.localSourceNode.disconnect()
    S.localSourceNode = source
    S.localGainNode = gainNode
    S.localSpeechFocusGainNode = speechFocusGainNode
    S.localSpeechDuckNode = speechDuckNode
    S.localGateNode = gateNode
    S.localAnalyser = analyser
    S.localAnalyserData = data
    S.localHighAnalyser = highAnalyser
    S.localHighAnalyserData = highData

    return destination.stream
  }

  const refreshMicDevices = async () => {
    if (!E.micDeviceSelect) return
    try {
      const devices = await navigator.mediaDevices.enumerateDevices()
      const mics = devices.filter((d) => d.kind === 'audioinput')
      const current = E.micDeviceSelect.value || S.voiceConfig.deviceId || ''
      E.micDeviceSelect.innerHTML = ''
      mics.forEach((d, i) => {
        const opt = document.createElement('option')
        opt.value = d.deviceId
        opt.textContent = d.label || `Mikrofon ${i + 1}`
        E.micDeviceSelect.appendChild(opt)
      })
      if (mics.length === 0) {
        const opt = document.createElement('option')
        opt.value = ''
        opt.textContent = 'Kein Mikrofon gefunden'
        E.micDeviceSelect.appendChild(opt)
      }

      const hasCurrent = Array.from(E.micDeviceSelect.options).some((o) => o.value === current)
      if (hasCurrent) E.micDeviceSelect.value = current
      syncVoiceConfigFromUi()
    } catch (_) {
    }
  }

  const updateVoiceUi = () => {
    E.voiceState.textContent = 'Voice Chat: ' + (S.voiceJoined ? 'im Chat' : 'offline')
    E.micState.textContent = 'Mic: ' + (S.voiceJoined ? (S.micMuted ? 'stumm' : 'an') : 'aus')
    E.partnerVoiceState.textContent = 'Partner Voice: ' + (S.partnerVoiceOnline ? (S.partnerMuted ? 'stumm' : 'online') : 'offline')

    if (E.selfVoiceBadge) E.selfVoiceBadge.textContent = 'Voice: ' + (S.voiceJoined ? (S.micMuted ? 'stumm' : 'im Chat') : 'aus')
    if (E.partnerVoiceBadge) E.partnerVoiceBadge.textContent = 'Voice: ' + (S.partnerVoiceOnline ? (S.partnerMuted ? 'stumm' : 'im Chat') : 'aus')
    if (E.selfNameLabel) E.selfNameLabel.classList.toggle('voice-in-chat', !!S.voiceJoined)
    if (E.partnerNameLabel) E.partnerNameLabel.classList.toggle('voice-in-chat', !!S.partnerVoiceOnline)

    E.btnVoiceJoin.disabled = S.voiceJoined
    E.btnVoiceLeave.disabled = !S.voiceJoined
    E.btnMicToggle.disabled = !S.voiceJoined
    E.btnMicToggle.textContent = S.micMuted ? 'Mic an' : 'Mic stumm'
    if (E.selfMicIcon) E.selfMicIcon.classList.toggle('hidden', !S.micMuted)
    if (E.partnerMicIcon) E.partnerMicIcon.classList.toggle('hidden', !S.partnerMuted)
    updateActivityUi()
  }

  const updateActivityUi = () => {}

  const updateStreamUi = () => {
    const live = !!S.localScreenStream
    if (E.localLiveDot) E.localLiveDot.classList.toggle('hidden', !live)
    if (E.btnStopShare) E.btnStopShare.classList.toggle('hidden', !live)
    if (E.btnSourceLive) E.btnSourceLive.classList.toggle('hidden', !live)
  }

  const addMsg = (m) => {
    const row = document.createElement('div')
    row.className = 'msg'
    const meta = document.createElement('div')
    meta.className = 'meta'
    const name = m.user_id === S.uid ? S.displayNames.self : S.displayNames.partner
    meta.textContent = `${name} • ${m.ts}`
    const body = document.createElement('div')
    body.textContent = m.message
    row.append(meta, body)
    E.chatLog.appendChild(row)
    E.chatLog.scrollTop = E.chatLog.scrollHeight
  }

  const sig = (type, data, target = null) => api('/api/chat/signals', {
    method: 'POST',
    body: JSON.stringify({ type, data, target })
  })

  const sendVoiceControl = (action) => sig('control', { feature: 'voice', action }).catch(() => {})

  const closePeer = () => {
    if (!S.pc) return
    try {
      S.pc.onicecandidate = null
      S.pc.onconnectionstatechange = null
      S.pc.ontrack = null
      S.pc.onnegotiationneeded = null
      S.pc.close()
    } catch (_) {
    }
    S.pc = null
    S.screenSender = null
    S.audioSender = null
    S.partnerStreamOnline = false
    S.partnerVoiceOnline = false
    S.partnerMuted = false
    E.remoteVideo.srcObject = null
    E.remoteState.textContent = 'wartet'
    E.remoteState.className = 'status'
    updateActivityUi()
  }

  const scheduleReconnect = (reason) => {
    if (S.reconnectTimer) return
    setConn(`Reconnecting (${reason})...`)
    S.reconnectTimer = window.setTimeout(async () => {
      S.reconnectTimer = null
      if (S.pc && ['connected', 'connecting'].includes(S.pc.connectionState)) return
      if (S.reconnecting) return
      S.reconnecting = true
      try {
        closePeer()
        pc()
        if (S.localScreenStream) await ensureVideoTrack()
        if (S.voiceJoined && S.localAudioStream) await ensureAudioTrack()
      } catch (_) {
      } finally {
        S.reconnecting = false
      }
    }, 1400)
  }

  function pc() {
    if (S.pc) return S.pc
    const p = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] })

    p.onicecandidate = (e) => {
      if (e.candidate) sig('ice', e.candidate).catch(() => {})
    }

    p.onconnectionstatechange = () => {
      const ok = ['connected', 'completed'].includes(p.connectionState)
      setConn(ok ? 'WebRTC verbunden' : ('WebRTC: ' + p.connectionState), ok)
      if (['failed', 'disconnected', 'closed'].includes(p.connectionState)) {
        scheduleReconnect('webrtc')
      }
    }

    p.ontrack = (e) => {
      const stream = e.streams[0] || new MediaStream([e.track])
      if (e.track.kind === 'video') {
        E.remoteVideo.srcObject = stream
        E.remoteState.textContent = 'online'
        E.remoteState.className = 'status ok'
        S.partnerStreamOnline = true
        updateActivityUi()
        e.track.addEventListener('ended', () => {
          S.partnerStreamOnline = false
          E.remoteState.textContent = 'wartet'
          E.remoteState.className = 'status'
          updateActivityUi()
        })
      }
      if (e.track.kind === 'audio' || stream.getAudioTracks().length > 0) {
        remoteAudio.srcObject = stream
        remoteAudio.play().catch(() => {})
        createAnalyser(stream, 'remote')
        ensureMeterLoop()
        S.partnerVoiceOnline = true
        S.partnerMuted = false
        updateVoiceUi()
        e.track.addEventListener('ended', () => {
          clearAnalyser('remote')
          S.partnerVoiceOnline = false
          S.partnerMuted = false
          updateVoiceUi()
        })
      }
    }

    p.onnegotiationneeded = async () => {
      try {
        S.making = true
        await p.setLocalDescription()
        await sig('offer', p.localDescription)
      } catch (_) {
      } finally {
        S.making = false
      }
    }

    S.pc = p
    return p
  }

  async function onSig(s) {
    const p = pc()

    if (s.type === 'control') {
      const d = s.data || {}
      if (d.feature === 'voice') {
        if (d.action === 'join') {
          S.partnerVoiceOnline = true
          S.partnerMuted = false
        } else if (d.action === 'leave') {
          clearAnalyser('remote')
          S.partnerVoiceOnline = false
          S.partnerMuted = false
        } else if (d.action === 'mute') {
          S.partnerVoiceOnline = true
          S.partnerMuted = true
        } else if (d.action === 'unmute') {
          S.partnerVoiceOnline = true
          S.partnerMuted = false
        }
        updateVoiceUi()
      }
      return
    }

    if (s.type === 'ice') {
      try {
        await p.addIceCandidate(s.data)
      } catch (_) {
        if (!S.ignore) console.warn('ice fail')
      }
      return
    }

    if (s.type === 'offer' || s.type === 'answer') {
      const coll = s.type === 'offer' && (S.making || p.signalingState !== 'stable')
      S.ignore = !S.polite && coll
      if (S.ignore) return
      await p.setRemoteDescription(s.data)
      if (s.type === 'offer') {
        await p.setLocalDescription()
        await sig('answer', p.localDescription, s.from)
      }
    }
  }

  async function ensureVideoTrack() {
    if (!S.localScreenStream) return
    const t = S.localScreenStream.getVideoTracks()[0]
    if (!t) return
    const p = pc()
    if (S.screenSender) await S.screenSender.replaceTrack(t)
    else S.screenSender = p.addTrack(t, S.localScreenStream)
  }

  async function ensureAudioTrack() {
    if (!S.localAudioStream) return
    const t = S.localAudioStream.getAudioTracks()[0]
    if (!t) return
    const p = pc()
    if (S.audioSender) await S.audioSender.replaceTrack(t)
    else S.audioSender = p.addTrack(t, S.localAudioStream)
  }

  async function share(mode) {
    try {
      const q = getQualityProfile()
      const st = await navigator.mediaDevices.getDisplayMedia({
        video: getDisplayVideoConstraints(mode),
        audio: false
      })
      if (S.localScreenStream) S.localScreenStream.getTracks().forEach((t) => t.stop())
      S.localScreenStream = st
      E.localVideo.srcObject = st
      const srcLabel = mode === 'screen' ? 'Bildschirm' : (mode === 'window' ? 'Fenster' : 'Quelle')
      E.localState.textContent = srcLabel + ` live (${q.label})`
      E.localState.className = 'status ok'
      const track = st.getVideoTracks()[0]
      track.addEventListener('ended', () => stopShare().catch(() => {}))
      await ensureVideoTrack()
      updateStreamUi()
      updateActivityUi()
    } catch (_) {
    }
  }

  async function stopShare() {
    if (S.localScreenStream) {
      S.localScreenStream.getTracks().forEach((t) => t.stop())
      S.localScreenStream = null
    }
    E.localVideo.srcObject = null
    E.localState.textContent = 'offline'
    E.localState.className = 'status'
    if (S.screenSender) {
      try { await S.screenSender.replaceTrack(null) } catch (_) {}
    }
    updateStreamUi()
    updateActivityUi()
  }

  async function joinVoice(silent = false) {
    if (S.voiceJoined) return
    try {
      syncVoiceConfigFromUi()
      const st = await navigator.mediaDevices.getUserMedia({
        audio: getLocalVoiceConstraints(),
        video: false
      })
      if (S.localRawAudioStream) S.localRawAudioStream.getTracks().forEach((t) => t.stop())
      if (S.localAudioStream) S.localAudioStream.getTracks().forEach((t) => t.stop())
      S.localRawAudioStream = st
      S.localAudioStream = buildLocalVoiceStream(st)
      resetGateStates()
      ensureMeterLoop()
      S.voiceJoined = true
      S.micMuted = false
      await ensureAudioTrack()
      await refreshMicDevices()
      if (!silent) sendVoiceControl('join')
      updateVoiceUi()
    } catch (e) {
      setConn('Voice-Fehler: ' + e.message, false, true)
    }
  }

  async function leaveVoice(silent = false) {
    if (S.localRawAudioStream) {
      S.localRawAudioStream.getTracks().forEach((t) => t.stop())
      S.localRawAudioStream = null
    }
    if (S.localAudioStream) {
      S.localAudioStream.getTracks().forEach((t) => t.stop())
      S.localAudioStream = null
    }
    if (S.audioSender) {
      try { await S.audioSender.replaceTrack(null) } catch (_) {}
    }
    if (S.localGainNode) {
      try { S.localGainNode.disconnect() } catch (_) {}
      S.localGainNode = null
    }
    if (S.localSpeechFocusGainNode) {
      try { S.localSpeechFocusGainNode.disconnect() } catch (_) {}
      S.localSpeechFocusGainNode = null
    }
    if (S.localSpeechDuckNode) {
      try { S.localSpeechDuckNode.disconnect() } catch (_) {}
      S.localSpeechDuckNode = null
    }
    if (S.localGateNode) {
      try { S.localGateNode.disconnect() } catch (_) {}
      S.localGateNode = null
    }
    clearAnalyser('local')
    resetGateStates()
    S.voiceJoined = false
    S.micMuted = false
    if (!silent) sendVoiceControl('leave')
    updateVoiceUi()
  }

  function toggleMute() {
    if (!S.voiceJoined) return
    S.micMuted = !S.micMuted
    sendVoiceControl(S.micMuted ? 'mute' : 'unmute')
    updateVoiceUi()
  }

  async function applyVoiceSettings() {
    const wasJoined = S.voiceJoined
    const wasMuted = S.micMuted
    const wasMicTestRunning = S.micTest.running
    syncVoiceConfigFromUi()

    if (wasMicTestRunning) {
      const appliedLive = await tryApplyTrackProcessingConstraints(S.micTest.stream)
      const activeDevice = getTrackDeviceId(S.micTest.stream)
      const selectedDevice = S.voiceConfig.deviceId || ''
      const needsDeviceSwitch = !!selectedDevice && selectedDevice !== activeDevice
      if (!appliedLive || needsDeviceSwitch) {
        if (E.micTestStatus) E.micTestStatus.textContent = 'Mic-Test: wird neu gestartet...'
        await stopMicTest(false)
        await startMicTest()
      }
    }

    if (!wasJoined) return

    const appliedLive = await tryApplyTrackProcessingConstraints(S.localRawAudioStream)
    const activeDevice = getTrackDeviceId(S.localRawAudioStream)
    const selectedDevice = S.voiceConfig.deviceId || ''
    const needsDeviceSwitch = !!selectedDevice && selectedDevice !== activeDevice
    if (!appliedLive || needsDeviceSwitch) {
      await leaveVoice(true)
      await joinVoice(true)

      if (wasMuted) {
        S.micMuted = true
        sendVoiceControl('mute')
        updateVoiceUi()
      }
    }
  }

  async function pollMsg() {
    const d = await api('/api/chat/messages?since=' + S.mid)
    ;(d.messages || []).forEach((m) => {
      S.mid = Math.max(S.mid, m.id || 0)
      addMsg(m)
    })
  }

  async function pollSig() {
    try {
      const d = await api('/api/chat/signals?since=' + S.sid)
      S.signalErrorCount = 0
      for (const s of (d.signals || [])) {
        S.sid = Math.max(S.sid, s.id || 0)
        await onSig(s)
      }
    } catch (_) {
      S.signalErrorCount += 1
      if (S.signalErrorCount >= 8) {
        S.signalErrorCount = 0
        scheduleReconnect('signal')
      }
    }
  }

  async function pollStatus() {
    await api('/api/chat/ping', { method: 'POST', body: '{}' })
    const d = await api('/api/chat/status')
    const on = (d.active_users || []).some((u) => u !== S.uid)
    E.partner.textContent = on ? 'online' : 'wartet...'
    E.partner.className = 'status ' + (on ? 'ok' : '')
    if (!on) {
      S.partnerStreamOnline = false
      if (!S.partnerVoiceOnline) {
        E.remoteState.textContent = 'wartet'
        E.remoteState.className = 'status'
      }
      updateActivityUi()
    }
  }

  async function send() {
    const m = E.input.value.trim()
    if (!m) return
    E.input.value = ''
    await api('/api/chat/messages', { method: 'POST', body: JSON.stringify({ message: m }) })
    await pollMsg()
  }

  function wireUi() {
    E.btnSend.onclick = () => send().catch((e) => setConn(e.message, false, true))
    E.input.onkeydown = (e) => { if (e.key === 'Enter') send().catch(() => {}) }

    if (E.streamQuality) {
      S.streamQuality = E.streamQuality.value || 'medium'
      E.streamQuality.onchange = () => {
        S.streamQuality = E.streamQuality.value || 'medium'
        applyQualityToActiveShare().catch(() => {})
      }
    }

    E.btnSharePicker.onclick = () => share('any')
    E.btnShareScreen.onclick = () => share('screen')
    E.btnShareWindow.onclick = () => share('window')
    if (E.btnSourceLive) E.btnSourceLive.onclick = () => share('any')
    E.btnStopShare.onclick = () => stopShare().catch(() => {})
    E.btnVoiceJoin.onclick = () => joinVoice().catch(() => {})
    E.btnVoiceLeave.onclick = () => leaveVoice().catch(() => {})
    E.btnMicToggle.onclick = () => toggleMute()

    const closeMenus = () => {
      if (E.menuStream) E.menuStream.classList.remove('open')
      if (E.menuVoice) E.menuVoice.classList.remove('open')
      if (E.menuSettings) E.menuSettings.classList.remove('open')
      if (E.micSettingsSubpanel) E.micSettingsSubpanel.classList.remove('open')
      if (E.btnMicSettings) E.btnMicSettings.classList.remove('open')
    }

    if (E.btnMenuStream && E.menuStream) {
      E.btnMenuStream.onclick = (ev) => {
        ev.stopPropagation()
        E.menuStream.classList.toggle('open')
        if (E.menuStream.classList.contains('open') && E.menuVoice) E.menuVoice.classList.remove('open')
        if (E.menuStream.classList.contains('open') && E.menuSettings) E.menuSettings.classList.remove('open')
      }
    }
    if (E.btnMenuVoice && E.menuVoice) {
      E.btnMenuVoice.onclick = (ev) => {
        ev.stopPropagation()
        E.menuVoice.classList.toggle('open')
        if (E.menuVoice.classList.contains('open') && E.menuStream) E.menuStream.classList.remove('open')
        if (E.menuVoice.classList.contains('open') && E.menuSettings) E.menuSettings.classList.remove('open')
      }
    }
    if (E.btnMenuSettings && E.menuSettings) {
      E.btnMenuSettings.onclick = (ev) => {
        ev.stopPropagation()
        E.menuSettings.classList.toggle('open')
        if (E.menuSettings.classList.contains('open') && E.menuStream) E.menuStream.classList.remove('open')
        if (E.menuSettings.classList.contains('open') && E.menuVoice) E.menuVoice.classList.remove('open')
        if (!E.menuSettings.classList.contains('open')) {
          if (E.micSettingsSubpanel) E.micSettingsSubpanel.classList.remove('open')
          if (E.btnMicSettings) E.btnMicSettings.classList.remove('open')
        }
      }
    }

    if (E.btnMicSettings && E.micSettingsSubpanel) {
      E.btnMicSettings.onclick = (ev) => {
        ev.stopPropagation()
        const open = E.micSettingsSubpanel.classList.toggle('open')
        E.btnMicSettings.classList.toggle('open', open)
      }
    }

    ;[E.menuStream, E.menuVoice, E.menuSettings, E.voiceSettingsPanel, E.micSettingsSubpanel].forEach((el) => {
      if (!el) return
      el.addEventListener('click', (ev) => ev.stopPropagation())
    })
    document.addEventListener('click', closeMenus)

    const bindCloseMenuAfter = (el) => {
      if (!el) return
      el.addEventListener('click', () => closeMenus())
    }
    bindCloseMenuAfter(E.btnSharePicker)
    bindCloseMenuAfter(E.btnShareScreen)
    bindCloseMenuAfter(E.btnShareWindow)
    bindCloseMenuAfter(E.btnVoiceJoin)
    bindCloseMenuAfter(E.btnMicToggle)
    bindCloseMenuAfter(E.btnVoiceLeave)

    if (E.btnRefreshMics) {
      E.btnRefreshMics.onclick = () => refreshMicDevices().catch(() => {})
    }

    const bindApply = (el, eventName = 'change') => {
      if (!el) return
      el.addEventListener(eventName, () => applyVoiceSettings().catch(() => {}))
    }

    const bindLive = (el, eventName = 'input', markPresetCustom = false) => {
      if (!el) return
      el.addEventListener(eventName, () => {
        syncVoiceConfigFromUi()
        if (markPresetCustom) setGatePresetCustomIfNeeded()
        resetGateStates()
      })
    }

    bindLive(E.micGain, 'input')
    bindApply(E.micDeviceSelect)
    bindLive(E.gateThreshold, 'input', true)
    bindLive(E.gateAttack, 'input', true)
    bindLive(E.gateHold, 'input', true)
    bindLive(E.gateRelease, 'input', true)
    bindLive(E.gateRange, 'input', true)
    bindLive(E.setGate, 'change')
    bindApply(E.setNoise)
    bindApply(E.setEcho)
    bindApply(E.setAgc)
    bindApply(E.setSpeechFocus)

    if (E.gatePreset) {
      E.gatePreset.addEventListener('change', () => {
        const selected = E.gatePreset.value || 'voice_strict'
        if (selected === 'custom') {
          syncVoiceConfigFromUi()
          resetGateStates()
          return
        }
        applyGatePreset(selected)
      })
    }

    if (E.selfDisplayName) E.selfDisplayName.addEventListener('input', syncDisplayNamesFromUi)
    if (E.partnerDisplayName) E.partnerDisplayName.addEventListener('input', syncDisplayNamesFromUi)
    if (E.roomTitleInput) E.roomTitleInput.addEventListener('input', syncRoomTitleFromUi)
    if (E.btnSwapNames) E.btnSwapNames.onclick = () => swapDisplayNames()

    if (E.btnMicTest) {
      E.btnMicTest.onclick = async () => {
        try {
          if (S.micTest.running) await stopMicTest(true)
          else await startMicTest()
        } catch (e) {
          if (E.micTestStatus) E.micTestStatus.textContent = 'Mic-Test: Fehler'
        }
      }
    }

    if (E.micTestLoopback) {
      E.micTestLoopback.onchange = async () => {
        if (!S.micTest.running) return
        try {
          await stopMicTest(false)
          await startMicTest()
        } catch (_) {
          if (E.micTestStatus) E.micTestStatus.textContent = 'Mic-Test: Fehler'
        }
      }
    }

    const doFullscreen = (target) => {
      if (!document.fullscreenElement) target.requestFullscreen().catch(() => {})
      else document.exitFullscreen().catch(() => {})
    }
    if (E.btnFullscreenLocal) E.btnFullscreenLocal.onclick = () => doFullscreen(E.localCard)
    if (E.btnFullscreenRemote) E.btnFullscreenRemote.onclick = () => doFullscreen(E.remoteCard)

    E.btnOpenTs.onclick = () => {
      const h = (location.hostname && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') ? location.hostname : '100.112.243.124'
      window.location.href = `ts3server://${h}?port=9987`
    }

    Array.from(document.querySelectorAll('button[data-expand]')).forEach((b) => {
      b.onclick = () => {
        const id = b.dataset.expand
        const c = $(id)
        const o = id === 'local-card' ? E.remoteCard : E.localCard
        const z = c.classList.contains('zoomed')
        E.localCard.classList.remove('zoomed', 'zoom-right', 'zoom-left', 'hidden')
        E.remoteCard.classList.remove('zoomed', 'zoom-right', 'zoom-left', 'hidden')
        if (!z) {
          c.classList.add('zoomed')
          c.classList.add(id === 'local-card' ? 'zoom-right' : 'zoom-left')
          o.classList.add('hidden')
        }
      }
    })

    window.addEventListener('beforeunload', () => {
      if (S.meterFrame) window.cancelAnimationFrame(S.meterFrame)
      if (S.reconnectTimer) window.clearTimeout(S.reconnectTimer)
      stopMicTest()
      closePeer()
      clearAnalyser('local')
      clearAnalyser('remote')
    })

    loadDisplayNames()
    loadRoomTitle()
    applyGatePreset('voice_strict')
    setAmpelState(0)
    updateVoiceUi()
    updateStreamUi()
  }

  ;(async () => {
    wireUi()
    await refreshMicDevices().catch(() => {})
    try {
      const b = await api('/api/chat/bootstrap')
      S.uid = b.user_id
      E.me.textContent = ''
      setConn('Verbunden', true)

      setInterval(() => pollMsg().catch(() => {}), 800)
      setInterval(() => pollSig().catch(() => {}), 250)
      setInterval(() => pollStatus().catch(() => {}), 3000)

      await pollMsg()
      await pollStatus()
    } catch (e) {
      setConn('Init fehlgeschlagen: ' + e.message, false, true)
    }
  })()
})()
