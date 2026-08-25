const isLocalFrontend = ["localhost", "127.0.0.1"].includes(window.location.hostname) && window.location.port !== "5000";
const API = window.PUSULA_API_URL || (isLocalFrontend ? "http://127.0.0.1:5000/api" : `${window.location.origin}/api`);

let authToken = null;
let refreshToken = null;
let currentUser = null;
let currentVisitorId = sessionStorage.getItem("pusula_visitor_id");
let currentProductId = null;
let currentBatchId = null;
let allResults = [];
let resultsPage = 1;
let resultsPages = 1;
let subSectorTags = [];
let competitorTags = [];
let supabaseAuth = null;
let currentSearchProfile = null;
let pendingTranslationSuggestion = null;

const $ = (id) => document.getElementById(id);

const topbar = $("topbar");
const userInitials = $("userInitials");
const userCompany = $("userCompany");
const logoutLink = $("logoutLink");

const pageLogin = $("page-login");
const pageForm = $("page-form");
const pageResults = $("page-results");
const pageDashboard = $("page-dashboard");
const pageModules = $("page-modules");

const loginForm = $("loginForm");
const loginUsername = $("loginUsername");
const loginPassword = $("loginPassword");
const loginButton = $("loginButton");
const googleLoginButton = $("googleLoginButton");
const loginError = $("loginError");
const loginCard = $("loginCard");
const consentBanner = $("consentBanner");
const consentYes = $("consentYes");
const consentNo = $("consentNo");
const consentStatus = $("consentStatus");

const productForm = $("productForm");
const oemInput = $("oemInput");
const hsCode = $("hsCode");
const productNameInput = $("productNameInput");
const productDescription = $("productDescription");
const mainSector = $("mainSector");
const saveDraftBtn = $("saveDraftBtn");
const classificationPanel = $("classificationPanel");
const classificationPath = $("classificationPath");
const classificationAliases = $("classificationAliases");
const confirmClassificationBtn = $("confirmClassificationBtn");
const classificationStatus = $("classificationStatus");

const resultsTitle = $("resultsTitle");
const resultsSummary = $("resultsSummary");
const statTotal = $("statTotal");
const statCountries = $("statCountries");
const statEmails = $("statEmails");
const statSubSector = $("statSubSector");
const filterCountry = $("filterCountry");
const filterSource = $("filterSource");
const filterPlatform = $("filterPlatform");
const filterMatch = $("filterMatch");
const searchInput = $("searchInput");
const resultsBody = $("resultsBody");
const resultsCount = $("resultsCount");
const newSearchBtn = $("newSearchBtn");
const exportBtn = $("exportBtn");

const loadingOverlay = $("loadingOverlay");
const loadingText = $("loadingText");
let assistantConversationId = null;
let currentFairAnalysisId = null;
let currentRFQSearchId = null;




loginForm.addEventListener("submit", handleLogin);
googleLoginButton.addEventListener("click", handleGoogleLogin);
logoutLink.addEventListener("click", (e) => {
  e.preventDefault();
  logout();
});
consentYes.addEventListener("click", () => UIController.handleConsentYes());
consentNo.addEventListener("click", () => UIController.handleConsentNo());
if ($("deleteVisitorEvent")) $("deleteVisitorEvent").addEventListener("click", deleteCurrentVisitorEvent);
productForm.addEventListener("submit", handleSearchBatch);
saveDraftBtn.addEventListener("click", handleSaveDraft);
newSearchBtn.addEventListener("click", () => goTo("form"));
exportBtn.addEventListener("click", handleExportBatch);
document.querySelectorAll("[data-module]").forEach(button => button.addEventListener("click", () => openModule(button.dataset.module)));
$("moduleBackBtn").addEventListener("click", () => goTo("dashboard"));
if ($("formBackBtn")) $("formBackBtn").addEventListener("click", () => goTo("dashboard"));
if ($("formBackFooterBtn")) $("formBackFooterBtn").addEventListener("click", () => goTo("dashboard"));
$("rfqStart").addEventListener("click", startRFQModule);
$("fairUpload").addEventListener("click", uploadFairModule);
$("fairUrlImport").addEventListener("click", importFairUrlModule);
$("fairListImport").addEventListener("click", importFairListModule);
$("fairStart").addEventListener("click", startFairModule);
$("rfqExport").addEventListener("click", () => downloadModuleExport(`/rfq-searches/${currentRFQSearchId}/exports`, "pusula-rfq.xlsx"));
$("fairExport").addEventListener("click", () => downloadModuleExport(`/fair-analyses/${currentFairAnalysisId}/exports`, "pusula-fuar-analizi.xlsx"));
$("assistantLauncher").addEventListener("click", openAssistant);
$("assistantClose").addEventListener("click", closeAssistant);
$("assistantForm").addEventListener("submit", sendAssistantMessage);
$("emailCampaignCreate").addEventListener("click", createEmailCampaign);
$("demandDraft").addEventListener("click", () => handleDemandAction(false));
$("demandApprove").addEventListener("click", () => handleDemandAction(true));
$("suggestTranslationsBtn").addEventListener("click", suggestTranslations);
$("applyTranslationsBtn").addEventListener("click", applyTranslationSuggestion);
$("tradeAnalyze").addEventListener("click", analyzeTradeMarket);
document.querySelectorAll(".step").forEach(el => {
  el.style.cursor = "pointer";
  el.addEventListener("click", () => {
    if (!authToken) return;
    const step = parseInt(el.dataset.step);
    if (step === 1) goTo("dashboard");
    else if (step === 2) goTo("form");
    else if (step === 3 && currentBatchId) goTo("results");
  });
});

if (oemInput) oemInput.addEventListener("input", () => oemInput.classList.remove("is-invalid"));
if (hsCode) hsCode.addEventListener("input", () => hsCode.classList.remove("is-invalid"));
if (productNameInput) {
  productNameInput.addEventListener("input", () => {
    productNameInput.classList.remove("is-invalid");
    currentSearchProfile = null;
    classificationPanel.hidden = true;
  });
  productNameInput.addEventListener("blur", suggestCategory);
}
if (confirmClassificationBtn) confirmClassificationBtn.addEventListener("click", () => {
  if (!currentSearchProfile) return;
  currentSearchProfile.confirmed = true;
  classificationStatus.textContent = "✓ Onaylandı";
  mainSector.value = currentSearchProfile.category_name || currentSearchProfile.category || "";
});

async function suggestCategory() {
  const productName = productNameInput.value.trim();
  if (productName.length < 2 || currentSearchProfile?.confirmed) return;
  try {
    const response = await postJson("/v2/products/classify", { product_name: productName });
    if (!response.ok) return;
    const data = await readApiPayload(response);
    currentSearchProfile = data.suggestions?.[0] || data;
    classificationPath.textContent = [currentSearchProfile.category_name, currentSearchProfile.subcategory_name].filter(Boolean).join(" › ") || "Genel ürün";
    const aliases = [...(currentSearchProfile.aliases_tr || []), ...(currentSearchProfile.aliases_en || [])];
    classificationAliases.textContent = aliases.length ? `Aramada kullanılacak eş anlamlılar: ${aliases.join(", ")}` : "Ürün adı doğrudan aranacak.";
    classificationStatus.textContent = "";
    classificationPanel.hidden = false;
  } catch (error) { console.warn("Kategori önerisi alınamadı", error); }
}

async function suggestTranslations() {
  const productName = productNameInput.value.trim();
  if (productName.length < 2) {
    $("translationSuggestionStatus").textContent = "Önce ürün adını yazın.";
    return;
  }
  $("translationSuggestionStatus").textContent = "Teknik terimler hazırlanıyor…";
  $("suggestTranslationsBtn").disabled = true;
  try {
    const response = await postJsonOrThrow("/v2/products/translate", { product_name: productName });
    const data = await readApiPayload(response);
    pendingTranslationSuggestion = data;
    const statusLabels = {
      ai_suggested: "AI tarafından önerildi; kaynak kontrolü gerekli",
      fallback_suggested: "Yerleşik sözlükten önerildi; kaynak kontrolü gerekli",
    };
    $("translationSuggestionText").textContent = `İngilizce öneri: ${data.validated_technical_term_en}`;
    $("translationEvidence").innerHTML = (data.evidence || []).map(item => `<a class="btn btn-ghost" href="${safeExternalUrl(item.url)}" target="_blank" rel="noopener">${escapeHtml(item.source)} üzerinde kontrol et ↗</a>`).join(" ");
    $("translationSuggestionStatus").textContent = statusLabels[data.verification_status] || "Kaynak kontrolü gerekli";
    $("translationSuggestionPanel").hidden = false;
  } catch (error) {
    $("translationSuggestionStatus").textContent = error.message;
  } finally {
    $("suggestTranslationsBtn").disabled = false;
  }
}

function applyTranslationSuggestion() {
  if (!pendingTranslationSuggestion) return;
  const translations = pendingTranslationSuggestion.translations || {};
  $("productNameEn").value = pendingTranslationSuggestion.validated_technical_term_en || translations.en || "";
  $("productNameDe").value = translations.de || "";
  $("productNameFr").value = translations.fr || "";
  $("productNameEs").value = translations.es || "";
  $("productNameRu").value = translations.ru || "";
  $("productNameAr").value = translations.ar || "";
  $("translationSuggestionStatus").textContent = "Öneriler kullanıcı onayıyla forma aktarıldı.";
}

filterCountry.addEventListener("change", renderFilteredResults);
filterSource.addEventListener("change", renderFilteredResults);
filterPlatform.addEventListener("change", renderFilteredResults);
filterMatch.addEventListener("change", renderFilteredResults);
let resultSearchTimer = null;
searchInput.addEventListener("input", () => {
  clearTimeout(resultSearchTimer);
  resultSearchTimer = setTimeout(() => renderFilteredResults(), 350);
});

initTagInput("subSectorsInput", "subSectorText", subSectorTags);
initTagInput("competitorsInput", "competitorText", competitorTags);
initSelectAll();
initImageUpload();
initGoogleAuth();
localStorage.removeItem("pusula_consent_answered");
loadCountryCatalog();

const savedToken = sessionStorage.getItem("pusula_token");
const savedRefreshToken = sessionStorage.getItem("pusula_refresh_token");
const savedUser = sessionStorage.getItem("pusula_user");
if (savedToken && savedUser) {
  authToken = savedToken;
  refreshToken = savedRefreshToken;
  currentUser = JSON.parse(savedUser);
  updateUserUI();
  goTo("dashboard");
}

setTimeout(() => {
  if (!authToken && !sessionStorage.getItem("pusula_token")) {
    showConsent();
  }
}, 800);


async function handleLogin(e) {
  if (e?.preventDefault) e.preventDefault();
  loginError.textContent = "";
  loginButton.disabled = true;
  loginButton.textContent = "Giriş yapılıyor…";

  try {
    const response = await fetch(`${API}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: loginUsername.value.trim(), password: loginPassword.value }),
    });
    const data = await readApiPayload(response);
    if (!response.ok) throw new Error(data.detail || "Giriş yapılamadı.");
    authToken = data.token;
    refreshToken = data.refresh_token || null;
    currentUser = data.user;

    sessionStorage.setItem("pusula_token", authToken);
    if (refreshToken) sessionStorage.setItem("pusula_refresh_token", refreshToken);
    sessionStorage.setItem("pusula_user", JSON.stringify(currentUser));

    hideConsent();
    updateUserUI();
    goTo("dashboard");
  } catch (err) {
    loginError.textContent = err.message || "Giriş hatası.";
  }

  loginButton.disabled = false;
  loginButton.textContent = "Giriş Yap";
}

async function initGoogleAuth() {
  try {
    if (!window.supabase?.createClient) throw new Error("Supabase giriş kütüphanesi yüklenemedi.");
    const response = await fetch(`${API}/auth/config`);
    const config = await readApiPayload(response);
    if (!response.ok) throw new Error(config.detail || "Google girişi yapılandırılmamış.");
    supabaseAuth = window.supabase.createClient(config.supabase_url, config.supabase_publishable_key);
    googleLoginButton.disabled = false;

    const { data, error } = await supabaseAuth.auth.getSession();
    if (error) throw error;
    if (data.session && !authToken) await completeSupabaseLogin(data.session);

    supabaseAuth.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_IN" && session && session.access_token !== authToken) {
        setTimeout(() => completeSupabaseLogin(session), 0);
      }
    });
  } catch (err) {
    console.warn("Google Auth başlatılamadı:", err);
  }
}

async function handleGoogleLogin() {
  loginError.textContent = "";
  if (!supabaseAuth) {
    loginError.textContent = "Google girişi henüz hazır değil.";
    return;
  }
  googleLoginButton.disabled = true;
  const { error } = await supabaseAuth.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: `${window.location.origin}/` },
  });
  if (error) {
    loginError.textContent = error.message || "Google girişi başlatılamadı.";
    googleLoginButton.disabled = false;
  }
}

async function completeSupabaseLogin(session) {
  try {
    const response = await fetch(`${API}/auth/me`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
    });
    const user = await readApiPayload(response);
    if (!response.ok) throw new Error(user.detail || "Google oturumu doğrulanamadı.");
    authToken = session.access_token;
    refreshToken = session.refresh_token || null;
    currentUser = user;
    sessionStorage.setItem("pusula_token", authToken);
    if (refreshToken) sessionStorage.setItem("pusula_refresh_token", refreshToken);
    sessionStorage.setItem("pusula_user", JSON.stringify(currentUser));
    hideConsent();
    updateUserUI();
    goTo("dashboard");
  } catch (err) {
    loginError.textContent = err.message || "Google girişi tamamlanamadı.";
  }
}

function showConsent() {
  if (
    authToken ||
    currentUser ||
    sessionStorage.getItem("pusula_token") ||
    (pageLogin && !pageLogin.classList.contains("visible"))
  ) {
    return;
  }
  consentBanner.style.display = "block";
  consentBanner.classList.remove("slide-out");
  consentBanner.classList.add("slide-in");
}

function hideConsent() {
  consentBanner.classList.remove("slide-in");
  consentBanner.classList.add("slide-out");
  setTimeout(() => {
    consentBanner.style.display = "none";
  }, 300);
}

async function logout() {
  if (supabaseAuth) {
    try {
      await supabaseAuth.auth.signOut();
    } catch {
      console.warn("Supabase oturumu uzaktan kapatılamadı; yerel oturum temizlendi.");
    }
  }
  authToken = null;
  refreshToken = null;
  currentUser = null;
  assistantConversationId = null;
  Object.keys(sessionStorage)
    .filter((key) => key.startsWith("pusula_"))
    .forEach((key) => sessionStorage.removeItem(key));
  currentVisitorId = null;
  updateVisitorPrivacyPanel();
  loginCard.style.display = "block";
  consentBanner.style.display = "none";
  consentBanner.classList.remove("slide-in", "slide-out");
  consentStatus.textContent = "";
  consentYes.disabled = false;
  consentNo.disabled = false;
  loginError.textContent = "";
  loginUsername.value = "";
  loginPassword.value = "";
  goTo("login");
}

function updateUserUI() {
  if (!currentUser) return;
  updateVisitorPrivacyPanel();
  const initials = currentUser.company_name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
  userInitials.textContent = initials;
  userCompany.textContent = currentUser.company_name;
}

class LocationService {
  static getCurrentPosition() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error("Tarayıcınız konum özelliğini desteklemiyor."));
        return;
      }

      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
        (err1) => {
          console.warn("Önbellek konumu alınamadı, canlı Wi-Fi konumuna bakılıyor...", err1.message);
          navigator.geolocation.getCurrentPosition(
            (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
            (err2) => {
              console.warn("Standart Wi-Fi konumu alınamadı, yüksek hassasiyet deneniyor...", err2.message);
              navigator.geolocation.getCurrentPosition(
                (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
                (err3) => reject(err3),
                { enableHighAccuracy: true, timeout: 15000, maximumAge: 600000 }
              );
            },
            { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 }
          );
        },
        { enableHighAccuracy: false, timeout: 5000, maximumAge: 600000 }
      );
    });
  }
}

class ApiService {
  static async sendLocationData(data) {
    try {
      const res = await postJson("/visitor-events", data);
      if (res.ok) {
        const responseData = await readApiPayload(res);
        return responseData.id;
      }
    } catch (error) {
      console.error("API hatası:", error);
    }
    return null;
  }

  static async detectLocation(payload) {
    try {
      const res = await fetch(`${API}/location/detect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.ok) return await readApiPayload(res);
    } catch (err) {
      console.warn("Konum tespiti hatası:", err);
    }
    return null;
  }
}

class UIController {
  static async handleConsentYes() {
    hideConsent();
    let payload = { permission: true };
    let gpsOk = false;

    try {
      const coords = await LocationService.getCurrentPosition();
      payload.latitude = coords.latitude;
      payload.longitude = coords.longitude;
      gpsOk = true;
    } catch (gpsErr) {
      console.warn("GPS koordinatı alınamadı:", gpsErr.message);
    }

    const detection = await ApiService.detectLocation(payload);
    if (detection) {
      setCurrentVisitorId(detection.id);
      UIController._showDetectionBadge(detection, gpsOk);
    } else {
      const visitorId = await ApiService.sendLocationData({ permission: true });
      if (visitorId) setCurrentVisitorId(visitorId);
    }
  }

  static async handleConsentNo() {
    hideConsent();
    const detection = await ApiService.detectLocation({ permission: false });
    if (detection) {
      setCurrentVisitorId(detection.id);
      UIController._showDetectionBadge(detection, false);
    } else {
      const visitorId = await ApiService.sendLocationData({ permission: false });
      if (visitorId) setCurrentVisitorId(visitorId);
    }
  }

  static _showDetectionBadge() {
    const old = document.getElementById("_location_badge");
    if (old) old.remove();
  }
}




let COUNTRY_DOMAINS = {
  "Türkiye": ".tr",
  "Almanya": ".de",
  "ABD": ".com",
  "Birleşik Krallık": ".co.uk",
  "BAE": ".ae",
  "Polonya": ".pl",
  "Rusya": ".ru",
  "Bulgaristan": ".bg",
  "Gürcistan": ".ge",
  "Azerbaycan": ".az",
  "Fransa": ".fr",
  "İspanya": ".es",
  "İtalya": ".it",
  "Suudi Arabistan": ".sa",
  "Mısır": ".eg",
  "Hindistan": ".in",
  "Çin": ".cn",
  "Japonya": ".jp",
};

async function loadCountryCatalog() {
  try {
    const response = await apiFetch("/catalog/countries");
    if (!response.ok) return;
    const countries = (await readApiPayload(response)).countries || [];
    if (!countries.length) return;
    COUNTRY_DOMAINS = Object.fromEntries(countries.map(country => [country.name, country.domain]));
    const selected = new Set(
      [...document.querySelectorAll('input[name="country"]:checked')].map(input => input.value)
    );
    $("countryChips").innerHTML = countries.map(country => {
      const checked = selected.has(country.name) || country.name === "Türkiye" ? " checked" : "";
      return `<label class="chip"><input type="checkbox" name="country" value="${escapeHtml(country.name)}"${checked}>${escapeHtml(country.name)}</label>`;
    }).join("") + '<label class="chip" id="selectAllCountries" style="font-weight:600;"><input type="checkbox">+ İlk 10 Pazarı Seç</label>';
    initSelectAll();
    enforceCountrySelectionLimit(10);
  } catch (error) {
    console.warn("Ülke kataloğu alınamadı", error);
  }
}

function updateVisitorPrivacyPanel() {
  const panel = $("visitorPrivacyPanel");
  if (panel) panel.hidden = !currentVisitorId || !authToken;
  const btn = $("deleteVisitorEvent");
  if (btn) btn.disabled = !currentVisitorId;
}

function setCurrentVisitorId(visitorId) {
  currentVisitorId = visitorId || null;
  if (currentVisitorId) sessionStorage.setItem("pusula_visitor_id", currentVisitorId);
  else sessionStorage.removeItem("pusula_visitor_id");
  updateVisitorPrivacyPanel();
}

async function deleteCurrentVisitorEvent() {
  if (!currentVisitorId) return;
  const response = await fetch(`${API}/visitor-events/${encodeURIComponent(currentVisitorId)}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const data = await readApiPayload(response);
    $("visitorPrivacyStatus").textContent = data.detail || "Konum kaydı silinemedi.";
    return;
  }
  setCurrentVisitorId(null);
  $("visitorPrivacyStatus").textContent = "Bu oturumdaki konum kaydı silindi.";
  $("deleteVisitorEvent").disabled = true;
}

function transformToProductCreate(rawForm) {
  const targetCountries = (rawForm.target_countries || []).map((countryName) => ({
    country_name: countryName,
    domain_extension: COUNTRY_DOMAINS[countryName] || null,
  }));

  const industries = [];
  if (rawForm.main_sector) {
    industries.push(rawForm.main_sector);
  }
  if (Array.isArray(rawForm.sub_sectors)) {
    rawForm.sub_sectors.forEach((sec) => {
      if (sec && !industries.includes(sec)) {
        industries.push(sec);
      }
    });
  }

  const productName = rawForm.product_name || "";

  return {
    oem: rawForm.oem,
    hs_code: rawForm.hs_code,
    name_tr: productName,
    name_en: rawForm.name_en || null,
    name_de: rawForm.name_de || null,
    name_fr: rawForm.name_fr || null,
    name_ru: rawForm.name_ru || null,
    name_es: rawForm.name_es || null,
    name_ar: rawForm.name_ar || null,
    description: rawForm.description || null,
    images: [],
    competitors: Array.isArray(rawForm.competitors) ? rawForm.competitors : [],
    industries: industries,
    target_countries: targetCountries,
    target_languages: rawForm.target_languages || ["İngilizce"],
    search_profile: currentSearchProfile || {},
  };
}

function collectFormData(status) {
  const countries = [
    ...document.querySelectorAll('input[name="country"]:checked'),
  ].map((el) => el.value);
  const languages = [
    ...document.querySelectorAll('input[name="language"]:checked'),
  ].map((el) => el.value);

  const sources = [];
  if ($("srcGoogleWeb").checked) sources.push("google_web");
  if (!$('srcYandexWeb').disabled && $("srcYandexWeb").checked) sources.push("yandex_web");
  if ($("srcGoogleMaps").checked) sources.push("google_maps");
  if ($("srcB2B").checked) sources.push("b2b_platform");

  return {
    company_name: currentUser ? currentUser.company_name : "Bilinmiyor",
    oem: oemInput.value.trim() || null,
    product_name: productNameInput.value.trim(),
    name_en: $("productNameEn").value.trim(),
    name_de: $("productNameDe").value.trim(),
    name_fr: $("productNameFr").value.trim(),
    name_ru: $("productNameRu").value.trim(),
    name_es: $("productNameEs").value.trim(),
    name_ar: $("productNameAr").value.trim(),
    hs_code: hsCode.value.trim() || null,
    description: productDescription.value.trim() || null,
    main_sector: mainSector.value.trim() || null,
    sub_sectors: subSectorTags,
    competitors: competitorTags,
    target_countries: countries,
    target_languages: languages,
    search_sources: sources,
    visitor_id: currentVisitorId,
    status: status,
  };
}

async function handleSaveDraft() {
  if (!productNameInput.value.trim()) {
    productNameInput.classList.add("is-invalid");
    productNameInput.focus();
    return;
  }
  productNameInput.classList.remove("is-invalid");

  saveDraftBtn.disabled = true;
  saveDraftBtn.textContent = "Kaydediliyor…";

  try {
    const payload = transformToProductCreate(collectFormData("draft"));
    const res = await postJson("/v2/products", payload);
    if (res.ok) {
      const data = await readApiPayload(res);
      currentProductId = data.id;
      saveDraftBtn.textContent = "✓ Kaydedildi";
      setTimeout(() => {
        saveDraftBtn.textContent = "Taslak Olarak Kaydet";
        saveDraftBtn.disabled = false;
      }, 2000);
    } else {
      saveDraftBtn.textContent = "Hata oluştu";
      saveDraftBtn.disabled = false;
    }
  } catch {
    saveDraftBtn.textContent = "Hata oluştu";
    saveDraftBtn.disabled = false;
  }
}

async function handleSearchBatch(e) {
  e.preventDefault();
  if (!productNameInput.value.trim()) {
    productNameInput.classList.add("is-invalid");
    productNameInput.focus();
    alert("Ürün adı zorunludur.");
    return;
  }
  if (!currentSearchProfile?.confirmed) {
    await suggestCategory();
    classificationPanel.scrollIntoView({ behavior: "smooth", block: "center" });
    alert("Doğru sonuçlar için önerilen ürün kategorisini onaylayın.");
    return;
  }
  const form = collectFormData("active");
  const countries = form.target_countries.length ? form.target_countries : ["Türkiye"];
  const sources = form.search_sources.length ? form.search_sources : ["google_web", "google_maps", "b2b_platform"];
  showLoading("Ürün bilgileri kaydediliyor…");
  try {
    const productRes = await postJson("/v2/products", transformToProductCreate(form));
    const product = await readApiPayload(productRes);
    if (!productRes.ok) throw new Error(product.detail || "Ürün kaydedilemedi.");
    currentProductId = product.id;

    const imageInput = $("productImages");
    if (imageInput.files.length) {
      showLoading("Ürün görselleri yükleniyor…");
      const data = new FormData();
      [...imageInput.files].slice(0, 3).forEach(file => data.append("files", file));
      data.append("reverse_search", $("reverseImageSearch")?.checked ? "true" : "false");
      const imageRes = await apiFetch(`/v2/products/${currentProductId}/images`, { method: "POST", body: data });
      const imageData = await readApiPayload(imageRes);
      if (!imageRes.ok) throw new Error(imageData.detail || "Görseller yüklenemedi.");
      if (imageData.reverse_search_status === "failed") {
        const message = imageData.images?.find(item => item.reverse_search_error)?.reverse_search_error;
        $("searchStatus").textContent = message || "Tersine görsel arama kullanılamadı; normal arama devam edecek.";
      }
    }

    showLoading(`${countries.length} pazar için görevler hazırlanıyor…`);
    const batchRes = await postJson("/search-batches", { product_id: currentProductId, target_countries: countries, sources });
    const batch = await readApiPayload(batchRes);
    if (!batchRes.ok) throw new Error(batch.detail || "Arama grubu oluşturulamadı.");
    currentBatchId = batch.id;
    const startRes = await postJson(`/search-batches/${currentBatchId}/start`, {});
    if (!startRes.ok) throw new Error((await readApiPayload(startRes)).detail || "Arama başlatılamadı.");

    for (let poll = 0; poll < 200; poll++) {
      await new Promise(resolve => setTimeout(resolve, 3000));
      const statusRes = await apiFetch(`/search-batches/${currentBatchId}/status`);
      if (!statusRes.ok) continue;
      const status = await readApiPayload(statusRes);
      const sourceNames = { google_web: "Google", yandex_web: "Yandex", google_maps: "Haritalar", b2b_platform: "B2B" };
      const jobText = (status.jobs || []).map(job =>
        `${sourceNames[job.source] || job.source}: ${job.status}${job.result_count ? ` (${job.result_count})` : ""}`
      ).join(" · ");
      showLoading(`Pazarlar taranıyor… %${status.progress || 0}${jobText ? ` — ${jobText}` : ""}`);
      if (["COMPLETED", "COMPLETED_WITH_ERRORS"].includes(status.status)) {
        await loadBatchResults(1);
        hideLoading();
        goTo("results");
        return;
      }
      if (["FAILED", "CANCELLED"].includes(status.status)) throw new Error("Arama görevleri başarısız oldu.");
    }
    await loadBatchResults(1);
    hideLoading();
    goTo("results");
    resultsSummary.textContent = "Arama arka planda devam ediyor. Bu ekranda şu ana kadar bulunan sonuçlar gösteriliyor.";
    return;
  } catch (err) {
    hideLoading();
    alert(err.message || "Arama sırasında hata oluştu.");
  }
}


function renderResults(data) {
  const stats = data.stats || {};

  resultsTitle.textContent = `${productNameInput.value.trim()} — Potansiyel Alıcılar`;
  resultsSummary.textContent = `${hsCode.value.trim() || "—"} kodu ve seçtiğiniz sektörlere göre ${stats.countries || 0} ülkede tarama tamamlandı.`;

  statTotal.textContent = stats.total || 0;
  statCountries.textContent = stats.countries || 0;
  statEmails.textContent = stats.emails_found || 0;
  statSubSector.textContent = stats.sub_sector_matches || 0;

  const selectedCountry = filterCountry.value;
  const selectedPlatform = filterPlatform.value;
  const countries = stats.country_options || [];
  filterCountry.innerHTML = '<option value="">Tüm Ülkeler</option>';
  countries.forEach((c) => {
    filterCountry.innerHTML += `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`;
  });
  filterCountry.value = selectedCountry;
  const platforms = stats.platform_options || [];
  filterPlatform.innerHTML = '<option value="">Tüm Platformlar</option>';
  platforms.forEach((platform) => {
    filterPlatform.innerHTML += `<option value="${escapeHtml(platform)}">${escapeHtml(platform)}</option>`;
  });
  filterPlatform.value = selectedPlatform;

  renderResultCards();
}

function renderResultCards() {
  const resultsPagination = $("resultsPagination");
  if (resultsPagination) {
    resultsPagination.textContent = `Sayfa ${resultsPage}/${resultsPages}`;
  }
  $("resultsPrev").disabled = resultsPage <= 1;
  $("resultsNext").disabled = resultsPage >= resultsPages;

  const COUNTRY_COLORS = {
    Almanya: "#4a4a4a",
    "Birleşik Krallık": "#12233d",
    Polonya: "#b8863a",
    ABD: "#2f7a56",
    BAE: "#a94a36",
    Gürcistan: "#5b6676",
    Bulgaristan: "#96692a",
    Azerbaycan: "#12233d",
    "Suudi Arabistan": "#a94a36",
    Rusya: "#2f7a56",
    Fransa: "#12233d",
    İspanya: "#b8863a",
    Türkiye: "#a94a36"
  };

  const SOURCE_LABELS = {
    google_web: "Google Web",
    yandex_web: "Yandex Web",
    google_maps: "Google Haritalar",
    b2b_platform: "B2B Platformu",
  };

  resultsBody.innerHTML = allResults
    .map((r) => {
      const dotColor = COUNTRY_COLORS[r.country] || "#9aa3b0";
      const matchClass = r.sector_match === "main" ? "match-high" : "match-mid";
      const matchLabel =
        r.sector_match === "main" ? "Ana sektör" : "Yan sektör";
      const sourceLabel = `${SOURCE_LABELS[r.source] || r.source}${r.platform ? ` · ${r.platform}` : ""}`;

      const websiteUrl = r.website
        ? r.website.startsWith("http")
          ? r.website
          : "https://" + r.website
        : "#";
      const mailTo = r.email ? `mailto:${r.email}` : "#";

      const address = r.address ? escapeHtml(r.address) : "Adres bilgisi bulunamadı";
      const phone = r.phone ? escapeHtml(r.phone) : "Telefon bilgisi bulunamadı";
      const email = r.email ? escapeHtml(r.email) : "E-posta bulunamadı";
      const emailEvidence = r.email_status === "verified" ? "Doğrulandı" : (r.email ? "Kamusal kaynak" : "");

      return `<div class="firm-card">
        <div class="firm-card-title">${escapeHtml(r.company_name)}</div>
        <div class="firm-detail-row">
          <svg class="firm-detail-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
          <div>${address}</div>
        </div>
        <div class="firm-actions-row">
          <div class="firm-detail-row">
            <svg class="firm-detail-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>
            <div>${phone}</div>
          </div>
          <div class="firm-detail-row">
            <svg class="firm-detail-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16v16H4z"></path><path d="m4 6 8 7 8-7"></path></svg>
            <div>${email}${emailEvidence ? ` · ${emailEvidence}` : ""}</div>
          </div>
        </div>
        
        <div class="firm-card-footer">
          <div class="firm-badges">
            <span class="flag-tag"><span class="flag-dot" style="background:${dotColor};"></span>${escapeHtml(r.country)}</span>
            <span class="match-pill ${matchClass}">${matchLabel}</span>
            <span class="source-chip">${sourceLabel}</span>
          </div>
          <div class="score-line">${escapeHtml(r.customer_type === "potential_customer" ? "Potansiyel alıcı" : r.customer_type === "seller_manufacturer" ? "Satıcı / üretici" : "Sektör adayı")} · İlgililik ${r.relevance_score || 0}/100 · Alıcı ${r.buyer_score || 0}/100${r.category_path ? ` · ${escapeHtml(r.category_path)}` : ""}</div>
          <div class="row-actions" style="margin-top:0;">
            <a class="icon-btn" href="${websiteUrl}" target="_blank" rel="noopener" title="Web sitesini aç">↗</a>
            <a class="icon-btn" href="${mailTo}" title="Mail gönder">✉</a>
          </div>
        </div>
      </div>`;
    })
    .join("");
}

function currentResultFilters() {
  return {
    country: filterCountry.value || null,
    source: filterSource.value || null,
    platform: filterPlatform.value || null,
    sector_match: filterMatch.value || null,
    min_relevance: 45,
    q: searchInput.value.trim() || null,
  };
}

async function loadBatchResults(page = 1) {
  if (!currentBatchId) return;
  const params = new URLSearchParams({ page: String(page), page_size: "25", min_relevance: "45" });
  Object.entries(currentResultFilters()).forEach(([key, value]) => {
    if (value !== null && key !== "min_relevance") params.set(key, value);
  });
  const response = await apiFetch(`/search-batches/${currentBatchId}/results?${params}`);
  if (!response.ok) throw new Error("Sonuçlar yüklenemedi.");
  const data = await readApiPayload(response);
  allResults = data.results || [];
  resultsPage = data.page || 1;
  resultsPages = data.pages || 1;
  resultsCount.textContent = `Arama sonucunda ${data.total || 0} adet firma bulundu.`;
  $("resultsCountFooter").textContent = `${data.total || 0} sonuç`;
  renderResults(data);
}

async function renderFilteredResults() {
  try {
    await loadBatchResults(1);
  } catch (error) {
    alert(error.message);
  }
}

const directorySearchBtn = $("directorySearchBtn");
const resetSearchLink = $("resetSearchLink");

if (directorySearchBtn) {
  directorySearchBtn.addEventListener("click", renderFilteredResults);
}
$("resultsPrev").addEventListener("click", () => loadBatchResults(resultsPage - 1));
$("resultsNext").addEventListener("click", () => loadBatchResults(resultsPage + 1));
if (resetSearchLink) {
  resetSearchLink.addEventListener("click", (e) => {
    e.preventDefault();
    searchInput.value = "";
    filterCountry.value = "";
    filterSource.value = "";
    filterPlatform.value = "";
    filterMatch.value = "";
    renderFilteredResults();
  });
}

async function handleExportBatch() {
  if (!currentBatchId) {
    alert("Lütfen önce bir arama işlemi gerçekleştirin.");
    return;
  }
  exportBtn.disabled = true;
  exportBtn.textContent = "Hazırlanıyor…";
  try {
    const createRes = await postJson(`/search-batches/${currentBatchId}/exports`, currentResultFilters());
    if (!createRes.ok) {
      const errData = await readApiPayload(createRes);
      throw new Error(errData.detail || "Rapor talebi oluşturulamadı.");
    }
    const created = await readApiPayload(createRes);
    let exportState = null;
    for (let i = 0; i < 60; i++) {
      await new Promise(resolve => setTimeout(resolve, 800));
      const statusRes = await apiFetch(`/exports/${created.id}`);
      if (!statusRes.ok) continue;
      exportState = await readApiPayload(statusRes);
      if (["COMPLETED", "FAILED"].includes(exportState.status)) break;
    }
    if (!exportState || exportState.status !== "COMPLETED") {
      throw new Error(exportState?.error_message || "Rapor hazırlanıyor. Lütfen birkaç saniye sonra tekrar deneyin.");
    }
    const downloadPath = exportState.download_url.startsWith("/api")
      ? exportState.download_url.substring(4)
      : exportState.download_url;
    const fileRes = await apiFetch(downloadPath);
    if (!fileRes.ok) throw new Error("Rapor dosyası indirilemedi.");
    const blob = await fileRes.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `pusula-sonuclar-${currentBatchId}.xlsx`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch (err) {
    alert(err.message || "Excel raporu indirilemedi.");
  } finally {
    exportBtn.textContent = "Excel Olarak İndir";
    exportBtn.disabled = false;
  }
}


function initTagInput(containerId, inputId, tagsArray) {
  const container = $(containerId);
  const input = $(inputId);

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const val = input.value.trim();
      if (val && !tagsArray.includes(val)) {
        tagsArray.push(val);
        renderTags(container, input, tagsArray);
      }
      input.value = "";
    }
  });
}

function renderTags(container, input, tagsArray) {
  container.querySelectorAll(".tag").forEach((t) => t.remove());

  tagsArray.forEach((tag, i) => {
    const el = document.createElement("span");
    el.className = "tag";
    el.innerHTML = `${escapeHtml(tag)} <button type="button">×</button>`;
    el.querySelector("button").addEventListener("click", () => {
      tagsArray.splice(i, 1);
      renderTags(container, input, tagsArray);
    });
    container.insertBefore(el, input);
  });
}


function initSelectAll() {
  const selectAll = $("selectAllCountries");
  if (!selectAll) return;
  const cb = selectAll.querySelector("input");

  cb.addEventListener("change", () => {
    [...document.querySelectorAll('input[name="country"]')].forEach((el, index) => {
      el.checked = cb.checked && index < 10;
    });
  });
}

function enforceCountrySelectionLimit(limit) {
  document.querySelectorAll('input[name="country"]').forEach(input => input.addEventListener("change", () => {
    const selected = document.querySelectorAll('input[name="country"]:checked');
    if (selected.length <= limit) return;
    input.checked = false;
    alert(`Bir aramada en fazla ${limit} ülke seçebilirsiniz.`);
  }));
}


function initImageUpload() {
  const input = $("productImages");
  const preview = $("uploadPreview");

  if (!input || !preview) return;

  input.addEventListener("change", () => {
    preview.innerHTML = "";
    [...input.files].slice(0, 3).forEach((file) => {
      const img = document.createElement("img");
      img.src = URL.createObjectURL(file);
      img.alt = file.name;
      preview.appendChild(img);
    });
  });
}


async function loadModuleProducts() {
  const response = await apiFetch("/v2/products?limit=1");
  if (!response.ok) return;
  const products = await readApiPayload(response);
  if (Array.isArray(products) && products.length > 0) {
    const sonUrun = products[0].name_tr || "";
    ["rfqProduct", "fairProduct", "demandProduct", "tradeProduct"].forEach(id => {
      const el = $(id);
      if (el && !el.value) el.value = sonUrun;
    });
  }
}

async function openModule(name) {
  if (name === "customer") { goTo("form"); return; }
  if (name === "assistant") { await openAssistant(); return; }
  goTo("modules");
  ["rfqModule", "fairModule", "learningModule", "emailModule", "demandModule", "planModule", "tradeModule"].forEach(id => $(id).hidden = true);
  $(`${name}Module`).hidden = false;
  if (["rfq", "fair", "demand", "trade"].includes(name)) await loadModuleProducts();
  if (name === "learning") await loadLearningLessons();
  if (name === "plan") await loadPlanDetails();
}

async function pollModule(basePath, id, statusEl, resultsEl, renderer) {
  for (let count = 0; count < 120; count++) {
    await new Promise(resolve => setTimeout(resolve, 2000));
    const response = await apiFetch(`${basePath}/${id}/status`);
    if (!response.ok) {
      if (response.status >= 500) continue;
      const error = await readApiPayload(response);
      throw new Error(error.detail || "İşlem durumu alınamadı");
    }
    const state = await readApiPayload(response);
    const rowProgress = state.total_rows ? ` · ${state.processed_rows || 0}/${state.total_rows} satır${state.duplicate_rows ? ` · ${state.duplicate_rows} tekrar` : ""}` : "";
    const warning = state.status === "COMPLETED_WITH_ERRORS" && state.error ? ` · ${state.error}` : "";
    statusEl.textContent = `${state.status} · %${state.progress || 0}${state.result_count ? ` · ${state.result_count} sonuç` : ""}${rowProgress}${warning}`;
    if (state.status === "COMPLETED" || state.status === "COMPLETED_WITH_ERRORS") {
      const resultResponse = await apiFetch(`${basePath}/${id}/results?page=1&page_size=100`);
      if (!resultResponse.ok) {
        const error = await readApiPayload(resultResponse);
        throw new Error(error.detail || "Sonuçlar alınamadı");
      }
      const data = await readApiPayload(resultResponse);
      const results = [...(data.results || [])];
      const pageCount = Math.ceil((data.total || results.length) / 100);
      for (let page = 2; page <= pageCount; page++) {
        const nextResponse = await apiFetch(`${basePath}/${id}/results?page=${page}&page_size=100`);
        if (!nextResponse.ok) break;
        results.push(...((await readApiPayload(nextResponse)).results || []));
      }
      resultsEl.innerHTML = results.map(renderer).join("") || '<div class="module-result">Uygun sonuç bulunamadı.</div>';
      return;
    }
    if (state.status === "FAILED") throw new Error(state.error || "İşlem başarısız oldu");
  }
  throw new Error("İşlem arka planda devam ediyor. Biraz sonra tekrar kontrol edin.");
}

function accessBadge(value) {
  const blocked = value !== "public";
  const labels = { public: "Açık kaynak", login_required: "Giriş gerekli", captcha_blocked: "CAPTCHA engeli", robots_blocked: "Robots engeli", enrichment_blocked: "Zenginleştirme yapılamadı" };
  return `<span class="access-badge ${blocked ? "blocked" : ""}">${labels[value] || value}</span>`;
}

async function startRFQModule() {
  const productId = $("rfqProduct").value.trim();
  if (!productId) { alert("Lütfen ürün adını yazın."); return; }
  $("rfqStatus").textContent = "RFQ taraması hazırlanıyor…";
  try {
    const createdResponse = await postJson("/rfq-searches", {
      product_id: productId,
      target_country: $("rfqCountry").value.trim() || "Türkiye",
      date_from: $("rfqDateFrom").value || null,
    });
    const created = await readApiPayload(createdResponse);
    if (!createdResponse.ok) throw new Error(created.detail || "RFQ oluşturulamadı");
    currentRFQSearchId = created.id;
    await postJsonOrThrow(`/rfq-searches/${created.id}/start`, {});
    await pollModule("/rfq-searches", created.id, $("rfqStatus"), $("rfqResults"), r => `<article class="module-result"><h3>${escapeHtml(r.title)}</h3><p>${escapeHtml(r.description || "")}</p><p>${accessBadge(r.access_status)} · İlgililik ${r.relevance_score}/100 · ${escapeHtml(r.platform || "Web")}</p><a href="${safeExternalUrl(r.source_url)}" target="_blank" rel="noopener">Platformda görüntüle ↗</a></article>`);
    $("rfqExport").hidden = false;
  } catch (error) { $("rfqStatus").textContent = error.message; }
}

async function uploadFairModule() {
  const file = $("fairFile").files[0];
  const productId = $("fairProduct").value.trim();
  if (!file || !productId) { alert("Lütfen ürün adını yazın ve XLSX/CSV dosyası seçin."); return; }
  $("fairStatus").textContent = "Dosya okunuyor…";
  const form = new FormData(); form.append("product_id", productId); form.append("file", file);
  try {
    const response = await apiFetch("/fair-analyses", { method: "POST", body: form });
    const data = await readApiPayload(response);
    if (!response.ok) throw new Error(data.detail || "Dosya yüklenemedi");
    prepareFairMapping(data);
  } catch (error) { $("fairStatus").textContent = error.message; }
}

async function importFairListModule() {
  const productId = $("fairProduct").value.trim();
  const entries = $("fairEntries").value.trim();
  if (!productId || !entries) { alert("Lütfen ürün adını yazın ve en az bir firma veya website ekleyin."); return; }
  $("fairStatus").textContent = "Katılımcı listesi hazırlanıyor…";
  try {
    const response = await postJson("/fair-analyses/from-list", { product_id: productId, entries });
    const data = await readApiPayload(response);
    if (!response.ok) throw new Error(data.detail || "Katılımcı listesi oluşturulamadı");
    prepareFairMapping(data);
    $("fairCompanyColumn").value = "Firma Adı";
    $("fairWebsiteColumn").value = "Website";
  } catch (error) { $("fairStatus").textContent = error.message; }
}

async function importFairUrlModule() {
  const productId = $("fairProduct").value.trim();
  const sourceUrl = $("fairSourceUrl").value.trim();
  if (!productId || !sourceUrl) { alert("Lütfen ürün adını ve açık katılımcı sayfası adresini yazın."); return; }
  $("fairStatus").textContent = "Açık katılımcı sayfası kontrol ediliyor…";
  try {
    const response = await postJson("/fair-analyses/from-url", { product_id: productId, source_url: sourceUrl });
    const data = await readApiPayload(response);
    if (!response.ok) throw new Error(data.detail || "Katılımcı sayfası okunamadı");
    if (!data.id) {
      $("fairStatus").textContent = data.detail || "Katılımcı bulunamadı.";
      return;
    }
    prepareFairMapping(data);
    $("fairCompanyColumn").value = "Firma Adı";
    $("fairWebsiteColumn").value = "Website";
  } catch (error) { $("fairStatus").textContent = error.message; }
}

function prepareFairMapping(data) {
  currentFairAnalysisId = data.id;
  const requiredOptions = data.columns.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join("");
  const optionalOptions = `<option value="">Seçilmedi</option>${requiredOptions}`;
  $("fairCompanyColumn").innerHTML = requiredOptions;
  ["fairWebsiteColumn", "fairCountryColumn", "fairCityColumn", "fairSectorColumn", "fairDescriptionColumn", "fairEmailColumn", "fairPhoneColumn"]
    .forEach(id => { $(id).innerHTML = optionalOptions; });
  $("fairMapping").hidden = false;
  $("fairStatus").textContent = `${data.total_rows || 0} katılımcı bulundu. Sütunları kontrol edip analizi başlatın.`;
}

async function startFairModule() {
  if (!currentFairAnalysisId) return;
  try {
    const mapping = {
      company_name: $("fairCompanyColumn").value,
      website: $("fairWebsiteColumn").value,
      country: $("fairCountryColumn").value,
      city: $("fairCityColumn").value,
      sector: $("fairSectorColumn").value,
      description: $("fairDescriptionColumn").value,
      email: $("fairEmailColumn").value,
      phone: $("fairPhoneColumn").value,
    };
    await postJsonOrThrow(`/fair-analyses/${currentFairAnalysisId}/column-mapping`, { mapping });
    await postJsonOrThrow(`/fair-analyses/${currentFairAnalysisId}/start`, {});
    await pollModule("/fair-analyses", currentFairAnalysisId, $("fairStatus"), $("fairResults"), r => `<article class="module-result"><h3>${escapeHtml(r.company_name)}</h3><p>${escapeHtml(r.sector || "Sektör belirtilmemiş")} · ${escapeHtml(r.country || "")}</p><p>${accessBadge(r.access_status)} · ${r.classification} · İlgililik ${r.relevance_score}/100 · Alıcı ${r.buyer_score}/100</p><p>${escapeHtml(r.match_reason || "")}</p></article>`);
    $("fairExport").hidden = false;
  } catch (error) { $("fairStatus").textContent = error.message; }
}

async function openAssistant() {
  if (!authToken) return;
  $("assistantPanel").classList.add("open"); $("assistantPanel").setAttribute("aria-hidden", "false");
  const storageKey = `pusula_assistant_${currentUser?.id || "user"}`;
  assistantConversationId = assistantConversationId || sessionStorage.getItem(storageKey);
  if (assistantConversationId) {
    const existing = await apiFetch(`/assistant/conversations/${assistantConversationId}`);
    if (existing.ok) {
      const conversation = await readApiPayload(existing);
      $("assistantMessages").innerHTML = conversation.messages.map(message => `<div class="assistant-message ${message.role === "user" ? "user" : "bot"}">${escapeHtml(message.content)}</div>`).join("");
      return;
    }
    assistantConversationId = null;
    sessionStorage.removeItem(storageKey);
  }
  if (!assistantConversationId) {
    const response = await postJson("/assistant/conversations", {});
    if (response.ok) {
      assistantConversationId = (await readApiPayload(response)).id;
      sessionStorage.setItem(storageKey, assistantConversationId);
    }
  }
}
function closeAssistant() { $("assistantPanel").classList.remove("open"); $("assistantPanel").setAttribute("aria-hidden", "true"); }
async function sendAssistantMessage(event) {
  event.preventDefault(); const content = $("assistantInput").value.trim();
  if (!content || !assistantConversationId) return;
  $("assistantMessages").insertAdjacentHTML("beforeend", `<div class="assistant-message user">${escapeHtml(content)}</div>`); $("assistantInput").value = "";
  const response = await postJson(`/assistant/conversations/${assistantConversationId}/messages`, { content });
  const data = await readApiPayload(response);
  if (!response.ok) {
    $("assistantMessages").insertAdjacentHTML("beforeend", `<div class="assistant-message bot">${escapeHtml(data.detail || "Yanıt alınamadı")}</div>`);
    return;
  }
  $("assistantMode").textContent = data.mode === "ai" ? "AI modu" : "Yardım modu";
  $("assistantMessages").insertAdjacentHTML("beforeend", `<div class="assistant-message bot">${escapeHtml(data.content || data.detail || "Yanıt alınamadı")}</div>`);
  $("assistantMessages").scrollTop = $("assistantMessages").scrollHeight;
}

async function downloadModuleExport(path, filename) {
  if (path.includes("/null/")) return;
  const response = await apiFetch(path, { method: "POST" });
  if (!response.ok) {
    const data = await readApiPayload(response);
    alert(data.detail || "Excel oluşturulamadı.");
    return;
  }
  const blob = await response.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(link.href);
}

async function loadLearningLessons() {
  const response = await apiFetch("/learning/lessons");
  if (!response.ok) {
    $("learningResults").textContent = "Dersler yüklenemedi.";
    return;
  }
  const lessons = await readApiPayload(response);
  $("learningResults").innerHTML = lessons.map(lesson => `<article class="module-result learning-lesson"><h3>${escapeHtml(lesson.title)}</h3><p>${escapeHtml(lesson.summary)}</p><p>${lesson.duration_minutes} dakika · %${lesson.progress}</p><details ${lesson.completed ? "" : "open"}><summary>Ders içeriğini aç</summary><ol>${(lesson.sections || []).map(section => `<li>${escapeHtml(section)}</li>`).join("")}</ol><fieldset ${lesson.completed ? "disabled" : ""}><legend>${escapeHtml(lesson.question)}</legend>${(lesson.options || []).map((option, index) => `<label><input type="radio" name="lesson_${escapeHtml(lesson.key)}" value="${index}"> ${escapeHtml(option)}</label>`).join("")}</fieldset><button class="btn btn-primary learning-complete" data-key="${escapeHtml(lesson.key)}" ${lesson.completed ? "disabled" : ""}>${lesson.completed ? "Tamamlandı" : "Cevabı Kontrol Et ve Tamamla"}</button><span class="learning-feedback"></span></details></article>`).join("");
  document.querySelectorAll(".learning-complete:not([disabled])").forEach(button => button.addEventListener("click", async () => {
    const lesson = button.closest(".learning-lesson");
    const selected = lesson.querySelector(`input[name="lesson_${button.dataset.key}"]:checked`);
    const feedback = lesson.querySelector(".learning-feedback");
    if (!selected) { feedback.textContent = "Bir cevap seçin."; return; }
    const response = await postJson(`/learning/lessons/${button.dataset.key}/complete`, { answer_index: Number(selected.value) });
    if (response.ok) { await loadLearningLessons(); return; }
    const error = await readApiPayload(response);
    feedback.textContent = error.detail || "Cevap kontrol edilemedi.";
  }));
}

async function createEmailCampaign() {
  const recipients = $("emailCampaignRecipients").value.split("\n").map(line => {
    const [email, fullName, companyName] = line.split(",").map(value => value.trim());
    return { email, full_name: fullName || null, company_name: companyName || null };
  }).filter(item => item.email);
  $("emailCampaignStatus").textContent = "Tanıtım taslağı kaydediliyor…";
  try {
    const response = await postJsonOrThrow("/email-campaigns", {
      name: $("emailCampaignName").value.trim(), subject: $("emailCampaignSubject").value.trim(),
      body: $("emailCampaignBody").value.trim(), recipients,
    });
    const campaign = await readApiPayload(response);
    $("emailCampaignStatus").textContent = "Tanıtım taslağı kaydedildi. Gönderim için aşağıdaki düğmeyle onay vermelisiniz.";
    $("emailCampaignResults").innerHTML = `<article class="module-result"><h3>${escapeHtml($("emailCampaignName").value.trim())}</h3><p>${campaign.recipient_count} alıcı · Taslak</p><button class="btn btn-primary" id="approveEmailCampaign">Onayla ve Gönder</button></article>`;
    $("approveEmailCampaign").addEventListener("click", async () => {
      if (!confirm(`${campaign.recipient_count} alıcıya bu tanıtım e-postasını göndermek istediğinizden emin misiniz?`)) return;
      try {
        const approved = await postJsonOrThrow(`/email-campaigns/${campaign.id}/approve`, { confirm_send: true });
        const data = await readApiPayload(approved);
        $("emailCampaignStatus").textContent = data.status === "QUEUED" ? "Tanıtım e-postaları gönderim kuyruğuna alındı." : data.status;
        await pollEmailCampaign(campaign.id);
      } catch (error) {
        $("emailCampaignStatus").textContent = error.message;
      }
    });
  } catch (error) {
    $("emailCampaignStatus").textContent = error.message;
  }
}

async function pollEmailCampaign(campaignId) {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    const response = await apiFetch(`/email-campaigns/${campaignId}`);
    if (!response.ok) return;
    const campaign = await readApiPayload(response);
    const metrics = campaign.metrics || {};
    $("emailCampaignResults").innerHTML = `<article class="module-result"><h3>Gönderim Durumu</h3><p>${escapeHtml(campaign.status)} · Gönderilen: ${metrics.sent || 0}/${metrics.total || 0} · Teslim: ${metrics.delivered || 0} · Bounce: ${metrics.bounced || 0} · Şikâyet: ${metrics.complained || 0} · Açılan: ${metrics.opened || 0} · Yanıtlanan: ${metrics.replied || 0} · Başarısız: ${metrics.failed || 0} · Abonelikten çıkan: ${metrics.unsubscribed || 0}</p><small>Teslim ve bounce değerleri yalnız imzalı sağlayıcı webhook'u bağlıysa kesinleşir. Açılma bilgisi yaklaşık bir sinyaldir.</small><br><button class="btn btn-secondary" id="syncEmailReplies">Yanıtları Kontrol Et</button></article>`;
    $("syncEmailReplies").addEventListener("click", () => syncEmailReplies(campaignId));
    if (["COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"].includes(campaign.status)) return;
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  $("emailCampaignStatus").textContent = "Gönderim arka planda devam ediyor. Durumu daha sonra tekrar kontrol edebilirsiniz.";
}

async function syncEmailReplies(campaignId) {
  try {
    const response = await postJsonOrThrow(`/email-campaigns/${campaignId}/sync-replies`, {});
    const data = await readApiPayload(response);
    $("emailCampaignStatus").textContent = `${data.matched} yanıt ve ${data.bounces || 0} teslim edilemedi bildirimi eşleştirildi.`;
    await pollEmailCampaign(campaignId);
  } catch (error) {
    $("emailCampaignStatus").textContent = error.message;
  }
}

async function handleDemandAction(autoApprove) {
  const productInput = $("demandProduct").value.trim();
  if (!productInput) { alert("Lütfen ürün adını yazın."); return; }
  const platforms = [...document.querySelectorAll('input[name="demandPlatform"]:checked')].map(item => item.value);
  if (!platforms.length) { alert("En az bir platform seçin."); return; }
  $("demandStatus").textContent = autoApprove ? "Talep oluşturuluyor ve yayınlanıyor…" : "Talep taslağı kaydediliyor…";
  try {
    const response = await postJsonOrThrow("/demand-posts", {
      product_id: productInput,
      quantity: $("demandQuantity").value.trim() || null,
      target_country: $("demandCountry").value.trim() || "Türkiye",
      deadline: $("demandDeadline").value || null,
      platforms,
    });
    const post = await readApiPayload(response);
    if (!autoApprove) {
      $("demandStatus").textContent = "Taslak başarıyla kaydedildi.";
      $("demandResults").innerHTML = `<article class="module-result"><h3>${escapeHtml(post.title || productInput)}</h3><p>${post.target_count} platform · Durum: Taslak</p><button class="btn btn-accent" id="approveDemandPost">Şimdi Onayla ve Yayınla</button></article>`;
      $("approveDemandPost").addEventListener("click", async () => {
        if (!confirm(`${post.target_count} platform için yayınlama işlemini başlatmak istiyor musunuz?`)) return;
        try {
          await postJsonOrThrow(`/demand-posts/${post.id}/approve`, { confirm_send: true });
          $("demandStatus").textContent = "Platform durumları kontrol ediliyor…";
          await pollDemandPost(post.id);
        } catch (error) {
          $("demandStatus").textContent = error.message;
        }
      });
    } else {
      await postJsonOrThrow(`/demand-posts/${post.id}/approve`, { confirm_send: true });
      $("demandStatus").textContent = "Platform durumları kontrol ediliyor…";
      await pollDemandPost(post.id);
    }
  } catch (error) {
    $("demandStatus").textContent = error.message;
  }
}

async function pollDemandPost(postId) {
  for (let count = 0; count < 60; count++) {
    await new Promise(resolve => setTimeout(resolve, 1500));
    const response = await apiFetch(`/demand-posts/${postId}`);
    if (!response.ok) continue;
    const post = await readApiPayload(response);
    if (["QUEUED", "PUBLISHING"].includes(post.status)) continue;
    $("demandStatus").textContent = post.status === "COMPLETED_WITH_ACTIONS" ? "Bazı platformlarda giriş yaparak tamamlamanız gerekiyor." : post.status;
    $("demandResults").innerHTML = post.targets.map(target => `<article class="module-result"><h3>${escapeHtml(target.platform)}</h3><p>${escapeHtml(target.status)}</p>${target.publication_url ? `<a href="${safeExternalUrl(target.publication_url)}" target="_blank" rel="noopener">Platformu aç ↗</a>` : ""}</article>`).join("");
    return;
  }
  $("demandStatus").textContent = "İşlem arka planda devam ediyor.";
}

async function loadPlanDetails() {
  const [rightsResponse, plansResponse] = await Promise.all([
    apiFetch("/account/entitlements"), apiFetch("/account/plans"),
  ]);
  if (!rightsResponse.ok || !plansResponse.ok) {
    $("planUsage").textContent = "Plan bilgileri alınamadı.";
    return;
  }
  const rights = await readApiPayload(rightsResponse);
  const plans = await readApiPayload(plansResponse);
  const remaining = rights.usage.remaining_searches === null ? "Sınırsız" : rights.usage.remaining_searches;
  $("planUsage").textContent = `Mevcut plan: ${rights.name} · Bu ay ${rights.usage.used_searches} arama kullanıldı · Kalan: ${remaining}`;
  $("planCards").innerHTML = plans.map(plan => `<article class="module-card ${plan.key === rights.plan ? "active" : ""}"><strong>${escapeHtml(plan.name)}</strong><small>${escapeHtml(plan.price_label)} · ${plan.monthly_searches === null ? "Sınırsız" : plan.monthly_searches} arama/ay</small><small>${plan.modules.length} modül</small>${plan.key === rights.plan ? "<span>Mevcut plan</span>" : "<span>Plan değişikliği için yöneticiyle iletişime geçin</span>"}</article>`).join("");
}

async function analyzeTradeMarket() {
  const productInput = $("tradeProduct").value.trim();
  if (!productInput) { alert("Lütfen ürün adı veya GTİP kodu yazın."); return; }
  $("tradeStatus").textContent = "UN Comtrade verisi alınıyor…";
  try {
    const year = Number.parseInt($("tradeYear").value, 10);
    const response = await postJsonOrThrow("/trade-markets/analyze", {
      product_id: productInput,
      target_country: $("tradeCountry").value.trim(),
      year: Number.isFinite(year) ? year : null,
    });
    const data = await readApiPayload(response);
    const value = new Intl.NumberFormat("tr-TR", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(data.import_value_usd);
    const weight = data.net_weight_kg == null ? "Belirtilmedi" : `${new Intl.NumberFormat("tr-TR").format(data.net_weight_kg)} kg`;
    $("tradeStatus").textContent = `${data.reporter_name || data.target_country} · ${data.period}`;
    $("tradeResults").innerHTML = `<article class="module-result"><h3>${escapeHtml(data.commodity || data.hs_code)}</h3><p>GTİP: ${escapeHtml(data.hs_code)} · Yıllık ithalat: ${escapeHtml(value)}</p><p>Net ağırlık: ${escapeHtml(weight)}</p><a href="${safeExternalUrl(data.source_url)}" target="_blank" rel="noopener">UN Comtrade kaynağını aç ↗</a></article>`;
  } catch (error) {
    $("tradeStatus").textContent = error.message;
  }
}

function goTo(name) {
  const pages = { login: pageLogin, dashboard: pageDashboard, modules: pageModules, form: pageForm, results: pageResults };
  Object.values(pages).forEach((p) => p.classList.remove("visible"));
  pages[name].classList.add("visible");

  topbar.style.display = name === "login" ? "none" : "flex";
  $("assistantLauncher").style.display = name === "login" ? "none" : "block";

  if (name === "login") {
    loginCard.style.display = "block";
  } else {
    hideConsent();
  }
  if (name === "dashboard" && authToken) loadCapabilities();

  const stepMap = { login: 1, dashboard: 1, modules: 2, form: 2, results: 3 };
  const current = stepMap[name];
  document.querySelectorAll(".step").forEach((el) => {
    const s = parseInt(el.dataset.step);
    el.classList.remove("active", "done");
    if (s < current) el.classList.add("done");
    if (s === current) el.classList.add("active");
  });
}


function postJson(path, body) {
  return apiFetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

async function loadCapabilities() {
  const panel = $("capabilityPanel");
  try {
    const response = await apiFetch("/capabilities");
    const data = await readApiPayload(response);
    if (!response.ok) throw new Error(data.detail || "Servis durumları alınamadı.");
    const items = data.capabilities || [];
    const unavailable = items.filter(item => item.status !== "ready");
    $("capabilityTitle").textContent = unavailable.length ? "Bazı servisler sınırlı çalışacak" : "Tüm servisler kullanıma hazır";
    $("capabilitySummary").textContent = `${data.ready_count}/${data.total_count} servis hazır. Yapılandırılmayan özelliklerde güvenli fallback veya manuel akış kullanılır.`;
    $("capabilityList").innerHTML = items.map(item => `<span class="capability-chip ${item.status === "ready" ? "" : "off"}" title="${escapeHtml(item.message)}">${escapeHtml(item.label)} · ${item.status === "ready" ? "Hazır" : "Sınırlı"}</span>`).join("");
    panel.hidden = false;
    const yandex = items.find(item => item.key === "yandex_web");
    if (yandex) {
      $("srcYandexWeb").disabled = yandex.status !== "ready";
      $("srcYandexWeb").checked = yandex.status === "ready";
      $("srcYandexStatus").textContent = yandex.message;
    }
  } catch (error) {
    $("capabilityTitle").textContent = "Servis durumları alınamadı";
    $("capabilitySummary").textContent = error.message;
    panel.hidden = false;
  }
}

async function postJsonOrThrow(path, body) {
  const response = await postJson(path, body);
  if (response.ok) return response;
  const data = await readApiPayload(response);
  throw new Error(data.detail || `İstek başarısız oldu (${response.status})`);
}

function responseErrorMessage(status, text) {
  const messages = {
    400: "Gönderilen bilgiler geçerli değil.",
    401: "Oturumunuz sona erdi. Lütfen yeniden giriş yapın.",
    403: "Bu işlem için yetkiniz bulunmuyor.",
    404: "İstenen kayıt bulunamadı.",
    409: "Bu işlem mevcut kayıtla çakışıyor.",
    413: "Gönderilen dosya çok büyük.",
    422: "Form alanlarını kontrol edin.",
    429: "Çok fazla istek gönderildi. Biraz bekleyip tekrar deneyin.",
    500: "Sunucuda beklenmeyen bir hata oluştu.",
    502: "Dış servisten geçerli yanıt alınamadı.",
    503: "Servis şu anda hazır değil.",
    504: "İşlem zaman aşımına uğradı.",
  };
  if (messages[status]) return messages[status];
  const normalized = String(text || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  return normalized && normalized.length <= 240 ? normalized : `İstek başarısız oldu (${status}).`;
}

async function readApiPayload(response) {
  const text = await response.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return { detail: responseErrorMessage(response.status, text) };
  }
}

async function apiFetch(path, options = {}, retry = true) {
  const headers = new Headers(options.headers || {});
  if (authToken) headers.set("Authorization", `Bearer ${authToken}`);
  const url = path.startsWith("http") ? path : API + path;
  const response = await fetch(url, { ...options, headers });
  if (response.status === 401 && retry && refreshToken) {
    const refreshResponse = await fetch(`${API}/auth/refresh`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (refreshResponse.ok) {
      const data = await readApiPayload(refreshResponse);
      authToken = data.token;
      refreshToken = data.refresh_token || refreshToken;
      sessionStorage.setItem("pusula_token", authToken);
      sessionStorage.setItem("pusula_refresh_token", refreshToken);
      return apiFetch(path, options, false);
    }
    logout();
  }
  return response;
}

function showLoading(text) {
  loadingText.textContent = text || "Yükleniyor…";
  loadingOverlay.classList.add("active");
}

function hideLoading() {
  loadingOverlay.classList.remove("active");
}

function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function safeExternalUrl(value) {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? escapeHtml(url.href) : "#";
  } catch {
    return "#";
  }
}
