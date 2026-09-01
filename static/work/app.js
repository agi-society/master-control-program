(function(){
  const visibility=document.getElementById('id_visibility');
  const shared=document.getElementById('id_visible_to');
  if(!visibility || !shared) return;
  const row=shared.closest('p');
  function syncPrivacy(){
    if(row) row.style.display=visibility.value==='private'?'grid':'none';
  }
  visibility.addEventListener('change',syncPrivacy);
  syncPrivacy();
})();

(function(){
  const board=document.getElementById('work-board');
  if(!board) return;
  const csrf=document.querySelector('#board-csrf input[name=csrfmiddlewaretoken]')?.value;
  const saveState=document.getElementById('board-save-state');
  let dragged=null;
  let saveTimer=null;

  function updateEmptyStates(){
    document.querySelectorAll('.board-dropzone').forEach(zone=>{
      const empty=zone.querySelector('.column-empty');
      if(empty) empty.style.display=zone.querySelector('.card')?'none':'flex';
    });
  }

  function getAfterElement(container,y){
    const cards=[...container.querySelectorAll('.card:not(.dragging)')];
    return cards.reduce((closest,card)=>{
      const box=card.getBoundingClientRect();
      const offset=y-box.top-box.height/2;
      if(offset<0 && offset>closest.offset) return {offset,element:card};
      return closest;
    },{offset:Number.NEGATIVE_INFINITY,element:null}).element;
  }

  function boardPayload(){
    const columns={};
    document.querySelectorAll('.board-column').forEach(column=>{
      const status=column.dataset.status;
      const cards=[...column.querySelectorAll('.card')];
      cards.forEach(card=>{
        [...card.classList].filter(c=>c.startsWith('status-')).forEach(c=>card.classList.remove(c));
        card.classList.add('status-'+status);
      });
      columns[status]=cards.map(card=>Number(card.dataset.workId));
    });
    return {work_id:Number(dragged?.dataset.workId || 0),columns};
  }

  async function saveBoard(){
    if(!dragged) return;
    const payload=boardPayload();
    saveState.textContent='Saving…';
    saveState.className='save-state saving';
    try{
      const response=await fetch('/board/reorder/',{
        method:'POST',
        headers:{'Content-Type':'application/json','X-CSRFToken':csrf},
        body:JSON.stringify(payload)
      });
      if(!response.ok) throw new Error(await response.text());
      saveState.textContent='Saved';
      saveState.className='save-state saved';
      clearTimeout(saveTimer);
      saveTimer=setTimeout(()=>{saveState.textContent='';},1400);
    }catch(error){
      console.error(error);
      saveState.textContent='Could not save — reloading';
      saveState.className='save-state error';
      setTimeout(()=>window.location.reload(),900);
    }
  }

  document.querySelectorAll('.card a').forEach(a=>a.draggable=false);
  board.addEventListener('dragstart',event=>{
    const card=event.target.closest('.card');
    if(!card) return;
    dragged=card;
    card.classList.add('dragging');
    event.dataTransfer.effectAllowed='move';
    event.dataTransfer.setData('text/plain',card.dataset.workId);
  });

  document.querySelectorAll('.board-dropzone').forEach(zone=>{
    zone.addEventListener('dragover',event=>{
      event.preventDefault();
      if(!dragged) return;
      const after=getAfterElement(zone,event.clientY);
      if(after) zone.insertBefore(dragged,after);
      else zone.insertBefore(dragged,zone.querySelector('.column-empty'));
      updateEmptyStates();
    });
    zone.addEventListener('drop',event=>{
      event.preventDefault();
      if(!dragged) return;
      updateEmptyStates();
      saveBoard();
    });
  });

  board.addEventListener('dragend',()=>{
    if(dragged) dragged.classList.remove('dragging');
    dragged=null;
    updateEmptyStates();
  });
  updateEmptyStates();
})();
