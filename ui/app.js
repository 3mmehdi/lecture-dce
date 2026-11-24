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
$$('.onglet').forEach((b) => b.addEventListener('click', () => {
  $$('.onglet').forEach((x) => { x.classList.toggle('actif', x === b); x.setAttribute('aria-pressed', x === b); });
  $('#vue-lire').hidden = b.dataset.vue !== 'lire';
  $('#vue-banc').hidden = b.dataset.vue !== 'banc';
  if (b.dataset.vue === 'banc') chargerComparaison();
}));
$$('.choix').forEach((b) => b.addEventListener('click', () => {
  mode = b.dataset.mode;
  $$('.choix').forEach((x) => { x.classList.toggle('actif', x === b); x.setAttribute('aria-checked', x === b); });
  $('#aide-mode').textContent = mode === 'direct'
    ? 'Appelle vraiment Claude : de 20 à 50 s par dossier selon la charge.'
    : 'Réaffiche les réponses mesurées le 24/11, sans appel. Utile si le réseau lâche.';
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
  $('#btn-brut').disabled = true; $('#brut').hidden = true; dernierBrut = null;
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
    const expl = EXPLIQUE.has(p.statut) && (p.pourquoi || p.que_faire);
    return `
    <li class="point ${p.statut} ${faux.includes(p.cle) ? 'faux' : ''}" style="--i:${i}">
      <button data-i="${i}" aria-pressed="false" ${expl ? `aria-expanded="false" aria-controls="expl-${p.cle}"` : ''}>
        <span class="nom">${esc(p.nom)}</span>
        <span class="statut ${p.statut}">${LIB[p.statut] || esc(p.statut) || '?'}</span>
        <span class="valeur">${esc(p.valeur)}</span>
        <span class="source">${p.source ? esc(p.source) : 'aucune source : rien dans le dossier'}</span>
        ${expl ? '<span class="indice">Pourquoi, et quoi faire</span>' : ''}
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
  viderReleve(); enCours = true; $('#btn-lire').disabled = true; $('#btn-lire').textContent = 'Lecture en cours…';
  let points = null, alertes = [], aFaire = [];
  try {
    await flux('/api/lire', { texte, cas: casChoisi, mode }, (e) => {
      if (e.etape === 'dossier') afficherFeuille(e.dossier);
      if (e.etape === 'consigne') etape('consigne', 'fait', `${e.taille.toLocaleString('fr-FR')} caractères`);
      if (e.etape === 'appel') { if (e.statut === 'rejoue') etape('appel', 'fait', `rejoué, ${e.modele}`); else { etape('appel', 'encours', 'en cours'); demarrerChrono(); } }
      if (e.etape === 'reponse') { arreterChrono(); if (mode === 'direct') etape('appel', 'fait', e.modele || 'terminé'); etape('reponse', 'fait', `${sec(e.duree_s)}, ${euros(e.cout_usd)}`); dernierBrut = e.brut; $('#btn-brut').disabled = false; }
      if (e.etape === 'controle') {
        const x = e.explications, expliques = x.a_expliquer - x.manquantes.length;
        etape('controle', e.ok ? 'fait' : 'echec', e.ok
          ? `12 clés${e.sans_source.length ? `, ${e.sans_source.length} sans source` : ''}, ${expliques}/${x.a_expliquer} risques expliqués`
          : `${e.manquantes.length} clés manquantes`);
      }
      if (e.etape === 'points') { points = e.points; alertes = e.alertes; aFaire = e.a_faire; afficherPoints(points, alertes, [], aFaire); if (!casChoisi) etape('notation', 'fait', 'pas de réponse attendue'); }
      if (e.etape === 'notation') {
        etape('notation', 'fait', `${e.points}/36, ${e.inventions} invention${e.inventions > 1 ? 's' : ''}`);
        afficherPoints(points, alertes, e.statuts_faux.map((f) => f.cle), aFaire);
        $('#notation').innerHTML = `Comparé à la réponse attendue, écrite avant le premier passage : <b>${e.points} points sur 36</b>, `
          + `<b>${e.inventions} valeur${e.inventions > 1 ? 's' : ''} inventée${e.inventions > 1 ? 's' : ''}</b>, `
          + `<b>${e.statuts_faux.length} statut${e.statuts_faux.length > 1 ? 's' : ''} faux</b>. Clique sur un point pour voir sa source dans le dossier, et sur un risque pour savoir pourquoi.`;
      }
      if (e.etape === 'erreur') { arreterChrono(); etape('appel', 'echec', 'échec'); $('#notation').innerHTML = `<p class="erreur">${esc(e.message)}</p>`; }
    });
  } catch (err) {
    arreterChrono(); $('#notation').innerHTML = `<p class="erreur">${esc(err.message)}</p>`;
  } finally {
    enCours = false; $('#btn-lire').disabled = false; $('#btn-lire').textContent = 'Lire le dossier';
  }
});

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

chargerCas();
