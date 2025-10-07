// Funções para Modais e Validações
document.addEventListener('DOMContentLoaded', function() {
    // Editar Quarto (preenche modal)
    window.editarQuarto = function(id, numero, tipo, preco, status) {
        document.getElementById('quartoId').value = id;
        document.getElementById('numero').value = numero;
        document.getElementById('tipo').value = tipo;
        document.getElementById('preco').value = preco;
        document.getElementById('status').value = status;
        new bootstrap.Modal(document.getElementById('modalQuarto')).show();
    };

   // Nova Reserva: Calcula total estimado e aviso de overlap
    const quartoSelect = document.getElementById('quartoSelect');
    const checkin = document.getElementById('checkin');
    const checkout = document.getElementById('checkout');
    const totalEstimado = document.getElementById('totalEstimado');
    const avisoOverlap = document.getElementById('avisoOverlap');

    function calcularTotal() {
        if (quartoSelect && quartoSelect.value && checkin && checkin.value && checkout && checkout.value) {
            const preco = parseFloat(quartoSelect.options[quartoSelect.selectedIndex].dataset.preco);
            const dataIn = new Date(checkin.value);
            const dataOut = new Date(checkout.value);
            const dias = (dataOut - dataIn) / (1000 * 60 * 60 * 24);
            if (dias > 0) {
                totalEstimado.value = (preco * dias).toFixed(2);
            } else {
                totalEstimado.value = 'Data inválida';
            }
        } else {
            totalEstimado.value = '';
        }
    }

    function verificarStatusQuarto() {
        if (quartoSelect && quartoSelect.value) {
            const status = quartoSelect.options[quartoSelect.selectedIndex].dataset.status;
            if (avisoOverlap && status !== 'Disponivel') {
                avisoOverlap.style.display = 'block';
            } else if (avisoOverlap) {
                avisoOverlap.style.display = 'none';
            }
        } else if (avisoOverlap) {
            avisoOverlap.style.display = 'none';
        }
    }

    if (quartoSelect) {
        quartoSelect.addEventListener('change', function() {
            calcularTotal();
            verificarStatusQuarto();  // Mostra aviso se quarto não disponível
        });
    }
    if (checkin) {
        checkin.addEventListener('change', function() {
            calcularTotal();
            if (checkout) checkout.min = checkin.value;
        });
    }
    if (checkout) {
        checkout.addEventListener('change', calcularTotal);
    }

    // Validação de datas (checkout > checkin)
    if (checkout && checkin) {
        checkout.addEventListener('change', function() {
            if (new Date(checkout.value) <= new Date(checkin.value)) {
                alert('Data de check-out deve ser posterior ao check-in.');
                checkout.value = '';
                totalEstimado.value = '';
            }
        });
    }
});