/* Build-time configuration. This is the ONLY file that differs between the StudyOS extension and the
   standalone Spatial extension (D:/PROJECTS/Spatial/extension/config.js). Loaded by the service worker
   (importScripts), the popup, the PDF viewer and injected before content.js. */
(function (root) {
  root.SPATIAL_CONFIG = {
    mode: 'studyos',                       // 'studyos' | 'standalone'
    productName: 'StudyOS Point & Ask',
    apiBase: 'http://127.0.0.1:8000',      // default server; user can change it in the popup
    dashboardUrl: 'http://127.0.0.1:8000/', // where history/tutor live (studyos mode)
    paths: {
      ask: '/api/spatial-context/ask',
      stream: '/api/spatial-context/ask/stream',
      health: '/api/health',
      transcribe: '/api/audio/transcribe',
      synthesize: '/api/audio/synthesize',
      login: '/api/auth/login',
      register: '/api/auth/register',
      quiz: '/api/spatial-context/{id}/quiz',
    },
    features: {
      accounts: true,          // sign in / anonymous device quota
      quizLater: true,         // "Quiz me later" → StudyOS review queue
      providerPicker: false,   // hosted product decides the provider; shown only in Power mode
      powerMode: true,         // local server audio + provider choice for self-hosters
    },
    anonymousDailyLimit: 20,
    protocolVersion: 2,
  };
})(typeof self !== 'undefined' ? self : this);
