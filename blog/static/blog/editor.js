document.addEventListener('DOMContentLoaded', () => {
  const source = document.getElementById('id_body');
  if (!source) return;
  const toolbar = document.createElement('div');
  toolbar.className = 'blog-editor-toolbar';
  toolbar.setAttribute('role', 'group');
  toolbar.setAttribute('aria-label', 'Article formatting');
  const editor = document.createElement('div');
  editor.className = 'blog-rich-editor';
  editor.contentEditable = 'true';
  editor.setAttribute('role', 'textbox');
  editor.setAttribute('aria-label', 'Article body');
  editor.setAttribute('aria-multiline', 'true');
  // Server sanitizes saved HTML; paste is plain text to avoid unsafe clipboard markup.
  editor.innerHTML = source.value;
  editor.addEventListener('input', () => { source.value = editor.innerHTML; });
  editor.addEventListener('paste', event => {
    event.preventDefault();
    document.execCommand('insertText', false, event.clipboardData.getData('text/plain'));
    source.value = editor.innerHTML;
  });
  const actions = [['Paragraph', 'formatBlock', 'p'], ['Heading', 'formatBlock', 'h2'], ['Subheading', 'formatBlock', 'h3'], ['Bold', 'bold'], ['Italic', 'italic'], ['Bullet list', 'insertUnorderedList'], ['Numbered list', 'insertOrderedList'], ['Quote', 'formatBlock', 'blockquote']];
  actions.forEach(([label, command, value]) => {
    const button = document.createElement('button');
    button.type = 'button'; button.textContent = label;
    button.addEventListener('mousedown', event => event.preventDefault());
    button.addEventListener('click', () => { editor.focus(); document.execCommand(command, false, value); source.value = editor.innerHTML; });
    toolbar.append(button);
  });
  source.before(toolbar, editor);
  source.hidden = true;
  const sourceButton = document.createElement('button');
  sourceButton.type = 'button'; sourceButton.textContent = 'Edit HTML';
  sourceButton.setAttribute('aria-pressed', 'false');
  sourceButton.addEventListener('click', () => {
    const showSource = source.hidden;
    if (showSource) source.value = editor.innerHTML;
    // Keep pasted source out of innerHTML until the server has sanitized it.
    if (!showSource) { source.closest('form').requestSubmit(); return; }
    source.hidden = false; editor.hidden = true;
    toolbar.querySelectorAll('button').forEach(button => { if (button !== sourceButton) button.disabled = true; });
    sourceButton.textContent = 'Save HTML'; sourceButton.setAttribute('aria-pressed', 'true');
    source.focus();
  });
  toolbar.append(sourceButton);
  source.closest('form').addEventListener('submit', () => { if (source.hidden) source.value = editor.innerHTML; });
});

