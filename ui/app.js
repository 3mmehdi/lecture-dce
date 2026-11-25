// Interface lecture-dce : lit les flux d'étapes renvoyés par app.py et les affiche.
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const LIB = { ok: 'sûr', risque: 'risque', eliminatoire: 'éliminatoire', a_verifier: 'à vérifier', non_trouve: 'non trouvé' };
const euros = (usd) => (usd ?? 0).toFixed(2).replace('.', ',') + ' $';
const sec = (s) => String(Math.round(s)) + ' s';

let mode = 'direct', cas = [], casChoisi = null, enCours = false, dernierBrut = null;

// ---------------------------------------------------------------- flux d'événements (POST + text/event-stream)
async function flux(url, corps, surEvenement) {
  const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corps) });
  if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.message || `Erreur ${r.status}`); }
  const lecteur = r.body.getReader(), dec = new TextDecoder();
  let tampon = '';
  for (;;) {
    const { value, done } = await lecteur.read();
    if (done) break;
    tampon += dec.decode(value, { stream: true });
    const blocs = tampon.split('\n\n'); tampon = blocs.pop();
    for (const b of blocs) if (b.startsWith('data: ')) surEvenement(JSON.parse(b.slice(6)));
  }
}

// ---------------------------------------------------------------- en-tête : vues et mode
function ouvrirVue(vue) {
  $$('.onglet').forEach((x) => { x.classList.toggle('actif', x.dataset.vue === vue); x.setAttribute('aria-pressed', x.dataset.vue === vue); });
  ['lire', 'claude', 'banc'].forEach((v) => { $(`#vue-${v}`).hidden = v !== vue; });
}
$$('.onglet').forEach((b) => b.addEventListener('click', () => {
  ouvrirVue(b.dataset.vue);
  if (b.dataset.vue === 'banc') chargerComparaison();
}));
$$('.choix').forEach((b) => b.addEventListener('click', () => {
  mode = b.dataset.mode;
  $$('.choix').forEach((x) => { x.classList.toggle('actif', x === b); x.setAttribute('aria-checked', x === b); });
  $('#aide-mode').textContent = mode === 'direct'
    ? 'Appelle vraiment Claude : de 20 à 50 s par dossier selon la charge.'
    : 'Réaffiche des réponses déjà mesurées, sans appel. Utile si le réseau lâche.';
}));

// ---------------------------------------------------------------- vue « lire »
async function chargerCas() {
  cas = await (await fetch('/api/cas')).json();
  $('#liste-cas').innerHTML = cas.map((c) =>
    `<li><button data-cas="${c.id}"><small>${c.id}</small>${esc(c.titre)}</button></li>`).join('');
  $$('#liste-cas button').forEach((b) => b.addEventListener('click', () => choisir(b.dataset.cas)));
  choisir('cas-03');
}

function choisir(id) {
  casChoisi = id;
  $('#zone-coller').hidden = true;
  $$('#liste-cas button').forEach((b) => b.setAttribute('aria-current', b.dataset.cas === id));
  const c = cas.find((x) => x.id === id);
  afficherFeuilleBrute(c.texte);
  viderReleve();
}

$('#btn-coller').addEventListener('click', () => {
  casChoisi = null;
  $$('#liste-cas button').forEach((b) => b.setAttribute('aria-current', false));
  $('#zone-coller').hidden = false;
  $('#texte-colle').focus();
  $('#feuille').innerHTML = '<p class="vide">Colle le texte du dossier à gauche, puis lance la lecture.</p>';
  viderReleve();
});

// Rendu local du dossier avant la réponse du serveur (même découpage que app.py : # titre, ## pièce, Art. n)
function afficherFeuilleBrute(texte) {
  const lignes = texte.split('\n').map((l, i) => {
    if (l.startsWith('# ')) return { id: i, type: 'titre', texte: l.slice(2) };
    if (l.startsWith('## ')) return { id: i, type: 'piece', texte: l.slice(3) };
    const m = l.match(/^\s*Art\.?\s*([0-9]+(?:\.[0-9]+)*)/i);
    return l.trim() ? { id: i, type: m ? 'article' : 'texte', texte: l.trim(), art: m ? m[1] : '' } : null;
  }).filter(Boolean);
  afficherFeuille({ lignes });
}

function afficherFeuille(d) {
  $('#feuille').innerHTML = d.lignes.map((l) => {
    if (l.type === 'titre') return `<h3>${esc(l.texte)}</h3>`;
    if (l.type === 'piece') return `<h4>${esc(l.texte)}</h4>`;
    if (l.type === 'article') {
      const reste = l.texte.replace(/^\s*Art\.?\s*[0-9.]+\s*/i, '');
      return `<p data-l="${l.id}"><span class="art">Art. ${esc(l.art)}</span>${esc(reste)}</p>`;
    }
    return `<p data-l="${l.id}">${esc(l.texte)}</p>`;
  }).join('');
}

function viderReleve() {
  $('#vide-releve').hidden = false; $('#alertes').innerHTML = ''; $('#points').innerHTML = ''; $('#notation').innerHTML = '';
  $('#bloc-a-faire').hidden = true; $('#a-faire').innerHTML = ''; $('#titre-points').hidden = true;
  $$('#etapes li').forEach((li) => { li.className = ''; $('span', li).textContent = '—'; });
  $('#btn-brut').disabled = true; $('#brut').hidden = true; dernierBrut = null; $('#btn-voir-claude').disabled = true;
}

function etape(nom, etat, texte) {
  const li = $(`#etapes li[data-e="${nom}"]`); if (!li) return;
  li.className = etat; $('span', li).textContent = texte;
}

let chrono = null;
function demarrerChrono() {
  const t0 = performance.now();
  chrono = setInterval(() => etape('appel', 'encours', `en cours, ${((performance.now() - t0) / 1000).toFixed(0)} s`), 500);
}
function arreterChrono() { clearInterval(chrono); chrono = null; }

function surligner(ids, bouton) {
  $$('#feuille p.cite').forEach((p) => p.classList.remove('cite', 'second'));
  $$('.point > button, #a-faire button').forEach((b) => b.setAttribute('aria-pressed', b === bouton));
  ids.forEach((id, i) => {
    const p = $(`#feuille p[data-l="${id}"]`);
    if (p) { p.classList.add('cite'); if (i > 0) p.classList.add('second'); }
  });
  const premier = ids.length && $(`#feuille p[data-l="${ids[0]}"]`);
  if (premier) {
    // Défilement de la seule zone du dossier : scrollIntoView ferait aussi défiler la page et cacherait l'en-tête
    const zone = $('.feuille-zone'), rz = zone.getBoundingClientRect(), rp = premier.getBoundingClientRect();
    const top = zone.scrollTop + rp.top - rz.top - rz.height / 2 + rp.height / 2;
    zone.scrollTo({ top, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }
}

const EXPLIQUE = new Set(['risque', 'eliminatoire', 'a_verifier']);

// Fait entrer l'explication ouverte dans la colonne de droite, sans faire défiler la page (même raison que pour la feuille)
function montrer(li) {
  const col = $('.releve');
  if (col.scrollHeight <= col.clientHeight) { li.scrollIntoView({ block: 'nearest' }); return; }
  const rc = col.getBoundingClientRect(), rl = li.getBoundingClientRect();
  const deborde = rl.bottom - rc.bottom + 12;
  if (deborde > 0) col.scrollBy({ top: Math.min(deborde, rl.top - rc.top - 8), behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
}

function explication(p) {
  return `<div class="explication" id="expl-${p.cle}" hidden>
      ${p.regle ? `<p class="regle"><b>Règle du skill</b>Cherché d'abord dans : ${esc(p.piece_habituelle)}. ${esc(p.regle)}<small>references/points.md : le statut se décide sur ces seuils, écrits avant les tests.</small></p>` : ''}
      ${p.pourquoi ? `<p><b>Pourquoi</b>${esc(p.pourquoi)}</p>` : ''}
      ${p.que_faire ? `<p><b>Ce qu'il faut faire</b>${esc(p.que_faire)}</p>` : ''}
      ${p.question ? `<div class="question"><b>Question à poser à l'acheteur</b><q>${esc(p.question)}</q>
        <button class="lien copier" data-q="${esc(p.question)}">Copier la question</button></div>` : ''}
      ${p.a_relire.length ? `<p class="a-relire">Absent du dossier, à relire : ${p.a_relire.map(esc).join(', ')}. C'est un calcul ou un seuil du skill, pas une valeur du marché.</p>` : ''}
    </div>`;
}

function afficherPoints(points, alertes, faux = [], aFaire = null) {
  $('#vide-releve').hidden = true;
  $('#titre-points').hidden = false;
  $('#alertes').innerHTML = (alertes || []).map((a) => `<p class="alerte">${esc(a)}</p>`).join('');
  if (aFaire) {
    $('#bloc-a-faire').hidden = !aFaire.length;
    $('#a-faire').innerHTML = aFaire.map((t, i) => `<li><button data-t="${i}" aria-pressed="false">
        <span class="quand">${esc(t.quand)}</span><span class="quoi">${esc(t.quoi)}</span></button></li>`).join('');
    $$('#a-faire button').forEach((b) => b.addEventListener('click', () => surligner(aFaire[b.dataset.t].lignes, b)));
  }
  const ol = $('#points');
  ol.classList.remove('arrive'); void ol.offsetWidth; ol.classList.add('arrive');
  ol.innerHTML = points.map((p, i) => {
    const explique = EXPLIQUE.has(p.statut) && (p.pourquoi || p.que_faire), expl = explique || p.regle;
    return `
    <li class="point ${p.statut} ${faux.includes(p.cle) ? 'faux' : ''}" style="--i:${i}">
      <button data-i="${i}" aria-pressed="false" ${expl ? `aria-expanded="false" aria-controls="expl-${p.cle}"` : ''}>
        <span class="nom">${esc(p.nom)}</span>
        <span class="statut ${p.statut}">${LIB[p.statut] || esc(p.statut) || '?'}</span>
        <span class="valeur">${esc(p.valeur)}</span>
        <span class="source">${p.source ? esc(p.source) : 'aucune source : rien dans le dossier'}</span>
        ${expl ? `<span class="indice">${explique ? 'Pourquoi, et quoi faire' : 'La règle appliquée'}</span>` : ''}
      </button>${expl ? explication(p) : ''}</li>`;
  }).join('');
  $$('.point > button', ol).forEach((b) => b.addEventListener('click', () => {
    const p = points[b.dataset.i], ouvrir = b.getAttribute('aria-expanded') === 'false';
    $$('.point > button[aria-expanded]', ol).forEach((x) => { x.setAttribute('aria-expanded', 'false'); $('#' + x.getAttribute('aria-controls')).hidden = true; });
    if (b.hasAttribute('aria-expanded') && ouvrir) { b.setAttribute('aria-expanded', 'true'); $('#expl-' + p.cle).hidden = false; montrer(b.parentElement); }
    surligner(p.lignes, b);
  }));
  $$('.copier', ol).forEach((b) => b.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(b.dataset.q); b.textContent = 'Question copiée'; }
    catch { b.textContent = 'Copie refusée : sélectionne le texte'; }
    setTimeout(() => (b.textContent = 'Copier la question'), 2000);
  }));
}

$('#btn-lire').addEventListener('click', async () => {
  if (enCours) return;
  const texte = casChoisi ? cas.find((c) => c.id === casChoisi).texte : $('#texte-colle').value;
  if (!texte.trim()) { $('#notation').innerHTML = '<p class="erreur">Le dossier est vide. Choisis un dossier ou colle son texte.</p>'; return; }
  viderReleve(); preparerClaude(casChoisi, true);
  enCours = true; $('#btn-lire').disabled = true; $('#btn-lire').textContent = 'Lecture en cours…';
  try {
    // Une seule conversation Claude Code : la fiche ici, le déroulé dans l'onglet « Dans Claude Code »
    await flux('/api/discussion', { texte, cas: casChoisi, mode, question: $('#claude-question').value },
      (e) => { traiterClaude(e); lectureDepuisClaude(e); });
  } catch (err) {
    arreterChrono(); $('#notation').innerHTML = `<p class="erreur">${esc(err.message)}</p>`;
  } finally {
    enCours = false; $('#btn-lire').disabled = false; $('#btn-lire').textContent = 'Lire le dossier';
  }
});

let lect = { points: null, alertes: [], aFaire: [] };
function traiterLecture(e) {
      if (e.etape === 'dossier') { afficherFeuille(e.dossier); lect = { points: null, alertes: [], aFaire: [] }; }
      if (e.etape === 'consigne') etape('consigne', 'fait', `${e.taille.toLocaleString('fr-FR')} caractères`);
      if (e.etape === 'appel') { if (e.statut === 'rejoue') etape('appel', 'fait', `rejoué, ${e.modele}`); else { etape('appel', 'encours', 'en cours'); demarrerChrono(); } }
      if (e.etape === 'reponse') { arreterChrono(); if (mode === 'direct') etape('appel', 'fait', e.modele || 'terminé'); etape('reponse', 'fait', `${sec(e.duree_s)}, ${euros(e.cout_usd)}`); dernierBrut = e.brut; $('#btn-brut').disabled = false; }
      if (e.etape === 'controle') {
        const x = e.explications, expliques = x.a_expliquer - x.manquantes.length;
        etape('controle', e.ok ? 'fait' : 'echec', e.ok
          ? `12 clés${e.sans_source.length ? `, ${e.sans_source.length} sans source` : ''}, ${expliques}/${x.a_expliquer} risques expliqués`
          : `${e.manquantes.length} clés manquantes`);
      }
      if (e.etape === 'points') { lect = { points: e.points, alertes: e.alertes, aFaire: e.a_faire }; afficherPoints(lect.points, lect.alertes, [], lect.aFaire); if (!casChoisi) etape('notation', 'fait', 'pas de réponse attendue'); }
      if (e.etape === 'notation') {
        etape('notation', 'fait', `${e.points}/36, ${e.inventions} invention${e.inventions > 1 ? 's' : ''}`);
        afficherPoints(lect.points, lect.alertes, e.statuts_faux.map((f) => f.cle), lect.aFaire);
        $('#notation').innerHTML = `Comparé à la réponse attendue, écrite avant le premier passage : <b>${e.points} points sur 36</b>, `
          + `<b>${e.inventions} valeur${e.inventions > 1 ? 's' : ''} inventée${e.inventions > 1 ? 's' : ''}</b>, `
          + `<b>${e.statuts_faux.length} statut${e.statuts_faux.length > 1 ? 's' : ''} faux</b>. Clique sur un point pour voir sa source dans le dossier, et sur un risque pour savoir pourquoi.`;
      }
      if (e.etape === 'erreur') { arreterChrono(); etape('appel', 'echec', 'échec'); $('#notation').innerHTML = `<p class="erreur">${esc(e.message)}</p>`; }
}

// Les étapes de la conversation, traduites pour le bandeau de la fiche
function lectureDepuisClaude(e) {
  if (['dossier', 'controle', 'points', 'notation', 'erreur'].includes(e.etape)) return traiterLecture(e);
  if (e.etape === 'demande') etape('consigne', 'encours', 'la question seule, sans consigne collée');
  if (e.etape === 'session') { if (e.rejoue) etape('appel', 'fait', 'conversation rejouée'); else { etape('appel', 'encours', 'en cours'); demarrerChrono(); } }
  if (e.etape === 'charge') etape('consigne', 'fait', `lecture-dce, ${milliers(e.caracteres)} caractères chargés`);
  if (e.etape === 'texte') {
    try { dernierBrut = JSON.parse(e.texte.match(/\{[\s\S]*\}/)[0]); $('#btn-brut').disabled = false; } catch { /* le serveur le signale */ }
  }
  if (e.etape === 'resultat') {
    arreterChrono();
    etape('appel', 'fait', `${e.tours} tours${e.rejoue ? ', rejoué' : ''}`);
    etape('reponse', 'fait', `${sec(e.duree_s)}, ${euros(e.cout_usd)}`);
    $('#btn-voir-claude').disabled = false;
  }
}

$('#btn-voir-claude').addEventListener('click', () => ouvrirVue('claude'));

$('#btn-brut').addEventListener('click', () => {
  const pre = $('#brut');
  pre.hidden = !pre.hidden;
  pre.textContent = JSON.stringify(dernierBrut, null, 2);
  $('#btn-brut').textContent = pre.hidden ? 'Voir la réponse brute' : 'Masquer la réponse brute';
});

// ---------------------------------------------------------------- vue « banc »
let comparaison = null;
async function chargerComparaison() {
  if (comparaison) return;
  comparaison = await (await fetch('/api/comparaison')).json();
  for (const v of ['v0.1', 'skill']) remplirVersion(v, comparaison[v]);
  remplirTableau();
  remplirCorriges();
}

function remplirVersion(v, d) {
  if (!d) return;
  const bloc = $(`#v-${CSS.escape(v)}`);
  $('.score', bloc).innerHTML = `${String(d.score).replace('.', ',')}<small> %</small>`;
  $('.chiffres', bloc).innerHTML = `<dt>Statuts faux</dt><dd>${d.statuts_faux}</dd><dt>Valeurs inventées</dt><dd>${d.inventions}</dd>`
    + (d.modele ? `<dt>Modèle</dt><dd>${esc(d.modele)}</dd>` : '') + (v === 'skill' && d.version ? `<dt>Version</dt><dd>${esc(d.version)}</dd>` : '');
}

function barre(points, skill) {
  if (points == null) return '<span class="barre-score">—</span>';
  return `<span class="barre-score ${skill ? 'skill' : ''}" style="--v:${points}"><i></i>${points}/36</span>`;
}

function remplirTableau() {
  const a = comparaison['v0.1']?.cas || [], b = comparaison.skill?.cas || [];
  $('#lignes-banc').innerHTML = cas.map((c) => {
    const x = a.find((l) => l.cas === c.id), y = b.find((l) => l.cas === c.id);
    return `<tr data-cas="${c.id}"><td>${esc(c.titre)}</td><td class="v01">${barre(x?.points)}</td><td class="v02">${barre(y?.points, true)}</td>`
      + `<td class="num">${y ? sec(y.duree_s) : '—'}</td><td class="num">${y ? euros(y.cout_usd) : '—'}</td></tr>`;
  }).join('');
}

function remplirCorriges() {
  const a = comparaison['v0.1']?.cas || [], b = comparaison.skill?.cas || [];
  const restants = b.reduce((n, l) => n + l.statuts_faux.length, 0);
  $('.corriges .sous').textContent = restants === 0
    ? 'Les statuts que la consigne simple rend faux, dossier par dossier. Le skill n\'en rate aucun.'
    : `Les statuts que la consigne simple rend faux. Le skill en rate encore ${restants}.`;
  $('#liste-corriges').innerHTML = a.flatMap((l) => {
    const titre = cas.find((c) => c.id === l.cas)?.titre || l.cas;
    return l.statuts_faux.map((f) => `<li><b>${esc(f.nom)}</b> <span>dans ${esc(titre)} : rendu « ${LIB[f.rendu] || esc(f.rendu)} », attendu « ${f.attendu.map((s) => LIB[s] || s).join(' ou ')} »</span></li>`);
  }).join('') || '<li>Aucun statut faux.</li>';
}

$$('[data-banc]').forEach((btn) => btn.addEventListener('click', async () => {
  if (enCours) return;
  const v = btn.dataset.banc, col = v === 'v0.1' ? '.v01' : '.v02';
  await chargerComparaison();
  enCours = true; $$('[data-banc]').forEach((b) => (b.disabled = true));
  const libelle = btn.textContent; btn.textContent = mode === 'direct' ? 'Évaluation en cours…' : 'Rejeu en cours…';
  const lignes = [];
  $$(`#lignes-banc ${col}`).forEach((td) => (td.innerHTML = '<span class="barre-score">en attente</span>'));
  try {
    await flux('/api/banc', { version: v, mode }, (e) => {
      if (e.etape === 'cas_debut') { const tr = $(`#lignes-banc tr[data-cas="${e.cas}"]`); tr.classList.add('encours'); $(col, tr).innerHTML = '<span class="barre-score">appel en cours</span>'; }
      if (e.etape === 'cas') {
        const tr = $(`#lignes-banc tr[data-cas="${e.cas}"]`); tr.classList.remove('encours');
        $(col, tr).innerHTML = barre(e.points, v === 'skill');
        if (v === 'skill') { $('td:nth-child(4)', tr).textContent = sec(e.duree_s); $('td:nth-child(5)', tr).textContent = euros(e.cout_usd); }
        lignes.push({ cas: e.cas, duree_s: e.duree_s, cout_usd: e.cout_usd, points: e.points, inventions: e.inventions, statuts_faux: e.statuts_faux });
      }
      if (e.etape === 'fin') {
        comparaison[v] = { ...comparaison[v], score: e.score, inventions: e.inventions, statuts_faux: lignes.reduce((n, l) => n + l.statuts_faux.length, 0), cas: lignes };
        remplirVersion(v, comparaison[v]); remplirCorriges();
      }
      if (e.etape === 'erreur') $('.corriges .sous').innerHTML = `<span class="erreur">${esc(e.message)}</span>`;
    });
  } catch (err) {
    $('.corriges .sous').innerHTML = `<span class="erreur">${esc(err.message)}</span>`;
  } finally {
    enCours = false; $$('[data-banc]').forEach((b) => (b.disabled = false)); btn.textContent = libelle;
  }
}));

// ---------------------------------------------------------------- vue « Dans Claude Code »
const PHASE = { session: 'session', outil: 'choix', charge: 'charge', lu: 'lu', texte: 'texte', controle: 'controle' };
const milliers = (n) => Number(n || 0).toLocaleString('fr-FR');
let ficheClaude = [];

function remplirSelectClaude() {
  $('#claude-cas').innerHTML = cas.map((c) => `<option value="${c.id}">${c.id} · ${esc(c.titre)}</option>`).join('')
    + '<option value="">Le dossier collé dans « Lire un dossier »</option>';
  $('#claude-cas').value = casChoisi || 'cas-03';
}

function phase(nom, etat) {
  const li = $(`#phases li[data-p="${nom}"]`); if (!li) return;
  $$('#phases li.encours').forEach((x) => { if (x !== li) x.classList.replace('encours', 'fait'); });
  li.className = etat;
}

function ajouterFil(html, classe = '') {
  $('#fil .attente')?.remove();
  const li = document.createElement('li'); li.className = classe; li.innerHTML = html;
  $('#fil').append(li);
  const z = $('.fil-zone'); z.scrollTo({ top: z.scrollHeight, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  return li;
}

function nomOutil(e) {
  if (e.nom === 'Skill') return `Skill<span>(${esc(e.detail)})</span>`;
  if (e.nom.startsWith('mcp__')) return `MCP · ${esc(e.nom.split('__').pop())}<span>(${esc(e.detail)})</span>`;
  const court = e.detail.replace(/\\/g, '/').replace(/^.*\/skills\/lecture-dce\//, '');
  return `${esc(e.nom)}<span>(${esc(court)})</span>`;
}

function traiterClaude(e) {
  if (e.etape === 'dossier') ficheClaude.push(e);
  if (e.etape === 'demande') {
    ajouterFil(`<p>${esc(e.question)}</p><small>${e.mcp ? 'dossier lu par l\'outil MCP · serveur lecture-dce branché' : `dossier joint · ${e.lignes} lignes`}</small>`, 'humain');
    ajouterFil('Claude Code démarre…', 'attente');
  }
  if (e.etape === 'session') {
    phase('session', 'fait');
    ajouterFil(`Session ${esc(e.modele)} · ${milliers(e.skills)} skills installés, dont lecture-dce : ${e.present ? 'oui' : 'non'}`, 'systeme');
    ajouterFil('Claude réfléchit…', 'attente');
  }
  if (e.etape === 'reflechit' && !$('#fil .attente')) ajouterFil('Claude réfléchit…', 'attente');
  if (e.etape === 'outil') {
    const mcp = e.nom.startsWith('mcp__'), controle = /verifier_reponse|noter_reponse/.test(e.nom);
    phase(e.nom === 'Skill' ? 'choix' : controle ? 'mcp' : 'lu', 'encours');
    ajouterFil(nomOutil(e), mcp ? 'outil mcp' : 'outil');
  }
  if (e.etape === 'mcp_controle') ajouterFil(`Contrôle : ${e.ok ? '12 clés, statuts connus' : `${e.manquantes} clé(s) manquante(s)`}, ${e.expliques}/${e.a_expliquer} risques expliqués`
    + ((e.absents || []).length ? `, <b>chiffre absent du dossier : ${e.absents.map(esc).join(', ')}</b>` : ''), 'retour note');
  if (e.etape === 'mcp_note') { phase('mcp', 'fait'); ajouterFil(`Note rendue par le serveur : <b>${e.points}/${e.sur}</b>, ${e.inventions} invention${e.inventions > 1 ? 's' : ''}, ${e.statuts_faux} statut${e.statuts_faux > 1 ? 's' : ''} faux`, 'retour note'); }
  if (e.etape === 'charge') {
    phase('choix', 'fait'); phase('charge', 'fait');
    const li = ajouterFil(`<span>Consigne du skill chargée : ${milliers(e.caracteres)} caractères</span> <button class="lien" type="button">voir le début</button><pre hidden></pre>`, 'retour');
    $('pre', li).textContent = e.debut;
    $('button', li).addEventListener('click', (ev) => { const p = $('pre', li); p.hidden = !p.hidden; ev.target.textContent = p.hidden ? 'voir le début' : 'masquer'; });
  }
  if (e.etape === 'lu') { phase('lu', 'fait'); ajouterFil(`${milliers(e.caracteres)} caractères lus`, 'retour'); }
  if (e.etape === 'texte') {
    phase('texte', 'fait');
    const li = ajouterFil('<pre></pre>', 'reponse-claude'); $('pre', li).textContent = e.texte;
    try { const m = e.texte.match(/\{[\s\S]*\}/); ficheClaude.push({ etape: 'reponse_brute', brut: JSON.parse(m[0]) }); } catch { /* le serveur le signale */ }
  }
  if (e.etape === 'resultat') {
    ficheClaude.push(e);
    ajouterFil(`${sec(e.duree_s)} · ${euros(e.cout_usd)} · ${e.tours} tours${e.rejoue ? ' · conversation enregistrée, rejouée' : ''}`, 'systeme');
    ecart(e);
  }
  if (['controle', 'points', 'notation'].includes(e.etape)) { ficheClaude.push(e); phase('controle', 'fait'); }
  if (e.etape === 'notation') {
    $('#note-claude').innerHTML = `Même notation que le banc : <b>${e.points} points sur 36</b>, <b>${e.inventions} invention${e.inventions > 1 ? 's' : ''}</b>, <b>${e.statuts_faux.length} statut${e.statuts_faux.length > 1 ? 's' : ''} faux</b>.`;
    $('#sortie-claude').hidden = false;
  }
  if (e.etape === 'fin' && $('#sortie-claude').hidden) { $('#note-claude').textContent = 'Dossier collé : pas de réponse attendue, donc pas de note.'; $('#sortie-claude').hidden = false; }
  if (e.etape === 'erreur') { $('#fil .attente')?.remove(); ajouterFil(esc(e.message), 'erreur'); }
}

// L'écart avec la lecture directe (consigne injectée, un seul tour), mesuré sur le même dossier
async function ecart(e) {
  const c = $('#claude-cas').value;
  if (!c) return;
  const r = await (await fetch('/api/comparaison')).json().catch(() => null);
  const ligne = r?.skill?.cas.find((x) => x.cas === c);
  if (!ligne) return;
  $('#ecart').hidden = false;
  $('#ecart').innerHTML = `<h3>Face au banc d'évaluation</h3><table>
    <tr><th></th><th>Banc : consigne injectée</th><th>Claude Code</th></tr>
    <tr><td>Qui choisit la consigne</td><td>l'interface</td><td>Claude</td></tr>
    <tr><td>Tours</td><td>1</td><td>${e.tours}</td></tr>
    <tr><td>Durée</td><td>${sec(ligne.duree_s)}</td><td>${sec(e.duree_s)}</td></tr>
    <tr><td>Coût</td><td>${euros(ligne.cout_usd)}</td><td>${euros(e.cout_usd)}</td></tr></table>
    <p>Le surcoût paie le choix du skill et la lecture de la référence. En échange, le chargé d'études n'a rien à coller : il pose sa question.</p>`;
}

function preparerClaude(c, depuisLire) {
  $('#fil').innerHTML = ''; $('#sortie-claude').hidden = true; $('#ecart').hidden = true; ficheClaude = [];
  $$('#phases li').forEach((li) => { li.className = ''; });
  $('#claude-cas').value = c || '';
  if (depuisLire) ajouterFil('Conversation lancée depuis « Lire un dossier » : la fiche affichée là-bas vient de cette réponse.', 'systeme');
}

$('#form-claude').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  if (enCours) return;
  const c = $('#claude-cas').value;
  const texte = c ? cas.find((x) => x.id === c).texte : $('#texte-colle').value;
  if (!texte.trim()) { ajouterFil('Aucun dossier collé dans « Lire un dossier ». Choisis un dossier de test ou colle d\'abord un texte.', 'erreur'); return; }
  preparerClaude(c || null, false);
  enCours = true; $('#btn-claude').disabled = true; $('#btn-claude').textContent = mode === 'direct' ? 'Claude Code travaille…' : 'Rejeu…';
  try {
    await flux('/api/discussion', { texte, cas: c || null, mode, question: $('#claude-question').value, mcp: $('#claude-mcp').checked }, traiterClaude);
  } catch (err) {
    ajouterFil(esc(err.message), 'erreur');
  } finally {
    enCours = false; $('#btn-claude').disabled = false; $('#btn-claude').textContent = 'Envoyer à Claude Code';
  }
});

// La même réponse, dans la vue fiche : on rejoue ses étapes dans traiterLecture
$('#btn-fiche').addEventListener('click', () => {
  const c = $('#claude-cas').value;
  casChoisi = c || null;
  $$('#liste-cas button').forEach((b) => b.setAttribute('aria-current', b.dataset.cas === c));
  ouvrirVue('lire'); viderReleve();
  const res = ficheClaude.find((x) => x.etape === 'resultat'), brut = ficheClaude.find((x) => x.etape === 'reponse_brute');
  etape('consigne', 'fait', 'choisie par Claude (skill)');
  etape('appel', 'fait', `Claude Code, ${res ? res.tours : '?'} tours`);
  ficheClaude.forEach((e) => {
    if (e.etape === 'resultat') traiterLecture({ etape: 'reponse', duree_s: e.duree_s, cout_usd: e.cout_usd, brut: brut?.brut });
    else if (e.etape !== 'reponse_brute') traiterLecture(e);
  });
});

chargerCas().then(remplirSelectClaude);
