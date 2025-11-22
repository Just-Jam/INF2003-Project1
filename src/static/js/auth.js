const csrftoken = document.cookie
  .split('; ')
  .find(row => row.startsWith('csrftoken='))
  ?.split('=')[1];

async function apiCall(url, method='POST', body=null){
  const resp = await fetch(url, {
    method,
    headers: {
      'X-CSRFToken': csrftoken,
      'Content-Type': 'application/json',
      'Authorization': localStorage.getItem('token') ? `Token ${localStorage.getItem('token')}` : ''
    },
    body: body ? JSON.stringify(body) : undefined
  });
  const data = await resp.json();
  if(!resp.ok) throw data;
  return data;
}

/* ---------- nav-bar logout ---------- */
document.getElementById('logoutBtn')?.addEventListener('click', async ()=>{
  await apiCall('/api/logout/', 'POST');
  localStorage.removeItem('token');
  location.href = '/login/';
});