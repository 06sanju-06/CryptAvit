// small helpers used by genkeys page
function downloadText(textareaId, filename) {
  const text = document.getElementById(textareaId).value;
  const blob = new Blob([text], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
console.log('cryptAVIT UI loaded');