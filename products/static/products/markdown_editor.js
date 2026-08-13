(() => {
  const escapeHtml = (value) => value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const safeUrl = (url) => /^(https?:\/\/|mailto:|\/|#)/i.test(url) ? url : '#';
  const inline = (value) => escapeHtml(value)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\[([^\]]+)\]\(([^\s)]+)\)/g, (_match, label, url) => `<a href="${safeUrl(url)}" target="_blank" rel="noopener noreferrer">${label}</a>`)
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/_([^_]+)_/g, '<em>$1</em>');

  const renderMarkdown = (value) => {
    let listType = null;
    const output = [];
    const closeList = () => { if (listType) output.push(`</${listType}>`); listType = null; };
    value.replace(/\r\n/g, '\n').split('\n').forEach((line) => {
      const unordered = line.match(/^\s*[-*+]\s+(.+)$/);
      const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);
      if (unordered || ordered) {
        const nextType = unordered ? 'ul' : 'ol';
        if (listType && listType !== nextType) closeList();
        if (!listType) { listType = nextType; output.push(`<${listType}>`); }
        output.push(`<li>${inline(unordered ? unordered[1] : ordered[1])}</li>`);
        return;
      }
      closeList();
      if (!line.trim()) return;
      const heading = line.match(/^(#{1,6})\s+(.+)$/);
      output.push(heading ? `<h${heading[1].length}>${inline(heading[2])}</h${heading[1].length}>` : `<p>${inline(line)}</p>`);
    });
    closeList();
    return output.join('');
  };

  const insert = (textarea, before, after = '') => {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = textarea.value.slice(start, end) || 'text';
    textarea.setRangeText(`${before}${selected}${after}`, start, end, 'end');
    textarea.focus();
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
  };

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('textarea.markdown-editor').forEach((textarea) => {
      const wrap = document.createElement('div');
      wrap.className = 'markdown-editor-wrap';
      textarea.parentNode.insertBefore(wrap, textarea);
      wrap.appendChild(textarea);

      const toolbar = document.createElement('div');
      toolbar.className = 'markdown-editor-toolbar';
      [['H2', '## ', ''], ['B', '**', '**'], ['I', '_', '_'], ['Link', '[', '](https://)'], ['List', '- ', ''], ['Code', '`', '`']].forEach(([label, before, after]) => {
        const button = document.createElement('button');
        button.type = 'button'; button.textContent = label;
        button.addEventListener('click', () => insert(textarea, before, after));
        toolbar.appendChild(button);
      });
      wrap.insertBefore(toolbar, textarea);

      const tabs = document.createElement('div');
      tabs.className = 'markdown-editor-tabs';
      const writeTab = document.createElement('button'); writeTab.type = 'button'; writeTab.textContent = 'Write'; writeTab.className = 'is-active';
      const previewTab = document.createElement('button'); previewTab.type = 'button'; previewTab.textContent = 'Preview';
      const preview = document.createElement('div'); preview.className = 'markdown-editor-preview'; preview.hidden = true;
      tabs.append(writeTab, previewTab); wrap.insertBefore(tabs, textarea); wrap.appendChild(preview);
      const showWrite = () => { textarea.hidden = false; preview.hidden = true; writeTab.classList.add('is-active'); previewTab.classList.remove('is-active'); };
      const showPreview = () => { preview.innerHTML = renderMarkdown(textarea.value); textarea.hidden = true; preview.hidden = false; previewTab.classList.add('is-active'); writeTab.classList.remove('is-active'); };
      writeTab.addEventListener('click', showWrite); previewTab.addEventListener('click', showPreview);
    });
  });
})();
