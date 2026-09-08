#Visão Geral

O sistema é uma plataforma web de mobilidade urbana sustentável destinada ao compartilhamento e à locação sob demanda de bicicletas distribuídas em estações estratégicas pela cidade. O objetivo central é fornecer uma alternativa ágil e econômica para trajetos urbanos de curta e média distância, integrando ciclistas, operadores de campo e administradores em um único ecossistema operacional que gerencia desde a frota até as transações financeiras.
Pelo navegador móvel, o ciclista consulta o mapa de estações com vagas e bicicletas disponíveis em tempo real, realizando o desbloqueio imediato por meio da leitura do QR Code fixado no veículo, que aciona a trava inteligente e inicia a contagem da corrida. O encerramento ocorre com o travamento da bicicleta em uma estação de destino autorizada, momento em que o sistema calcula a duração total do trajeto, emite o comprovante digital e permite o reporte de problemas mecânicos para bloqueio preventivo da unidade.
A cobrança é realizada de forma automatizada por tarifação fracionada por minuto ou mediante o consumo de pacotes de minutos pré-pagos, com liquidação digital integrada via PIX dinâmico, cartão de débito e cartão de crédito. Em paralelo, a plataforma oferece painéis para que operadores realizem a redistribuição logística de veículos entre estações e para que administradores monitorem relatórios analíticos de receita, ociosidade e manutenção da frota.


#Glossário

Bicicleta: unidade de transporte individual disponibilizada para locação. Possui identificador único (ID_Bicicleta) e status operacional (Disponível, Em Uso, Em Manutenção ou Bloqueada).
Estação: local físico destinado ao estacionamento, retirada e devolução das bicicletas. Possui ID_Estação, coordenadas geográficas (latitude/longitude), capacidade máxima de vagas e quantidade de vagas ocupadas e livres.
QR Code da Bicicleta: código bidimensional afixado fisicamente no quadro ou na trava de cada bicicleta. Armazena um identificador único ou URL segura que, ao ser lido pelo sistema web, mapeia a requisição diretamente para o ID_Bicicleta correspondente para autorização de desbloqueio.
Pacote de Minutos: saldo pré-pago adquirido pelo usuário que concede uma quantidade fixa de minutos de uso com validade determinada, consumido prioritariamente antes da cobrança avulsa por minuto.
Corrida (Locação): transação que compreende o intervalo entre o desbloqueio da bicicleta e a confirmação de devolução em uma estação. Registra data/hora de início e fim, ID_Bicicleta, ID_Usuário, estações de origem e destino, tempo total decorrido e valor final tarifado.
Registro de Problemas: notificação enviada pelo usuário ou operador relatando falhas físicas ou mecânicas (ex.: pneu furado, freio inoperante), alterando automaticamente o status da bicicleta para Em Manutenção.

#Requisitos Não Funcionais

Usabilidade (Usability)
RNF-01: A interface web para leitura da câmera e captura do QR Code deve carregar em menos de 3 segundos e permitir o acionamento da câmera em até 1 toque após a autenticação.
RNF-02: O frontend web deve ser totalmente responsivo, adaptando-se a telas de smartphones comuns.
RNF-03: O sistema deve fornecer retorno visual claro e imediato em todas as etapas da corrida (ex.: Aguardando liberação da trava, Corrida em andamento com cronômetro ativo, Devolução confirmada, Preço acumulado da corrida).
Confiabilidade (Reliability)
RNF-04: Caso o smartphone perca a conexão de dados durante o percurso, o estado da corrida e a contagem de tempo devem permanecer íntegros e sincronizados pelo backend via timestamp de início/fim registrado no servidor, independente do relógio do cliente.
RNF-05: O serviço de API deve manter disponibilidade mínima de 99% em horário de operação comercial.
Desempenho (Performance)
RNF-06: O tempo de resposta para validação de QR Code e autorização de início de corrida deve ser inferior a 500 ms.
RNF-07: A API deve suportar pelo menos 100 requisições simultâneas por segundo sem lentidão perceptível.
Segurança (Security)
RNF-08: A autenticação de usuários e operadores deve ser feita via tokens com tempo de expiração e senhas armazenadas com hash criptográfico seguro.
RNF-09: O sistema não deve persistir dados sensíveis de cartões (número completo, CVV) no banco de dados da aplicação.
Segurança (Safety)
RNF-10: O sistema não deve permitir o aluguel de bicicletas que estejam com problemas mecânicos relatados.
Tecnológicos
RNF-11: O backend deve ser obrigatoriamente implementado em Python 3.11+, utilizando o framework FastAPI. 
RNF-12: O banco de dados deve obrigatoriamente ser relacional.
Requisitos Funcionais
 RF-01 (Cadastro e Autenticação de Ciclista): O sistema deve permitir o cadastro e autenticação de usuários via e-mail e senha ou login social, validando CPF e dados de contato.
 RF-02 (Cadastro e Perfis de Operação): O sistema deve fornecer controle de acesso baseado em papéis (RBAC), separando permissões entre Ciclista, Operador de Campo e Administrador.
 RF-03 (Gerenciamento de Métodos de Pagamento): O sistema deve permitir que o usuário cadastre, consulte e remova cartões de crédito e débito tokenizados.
 RF-04 (Consulta de Estações no Mapa): O sistema deve exibir no mapa interativo as estações disponíveis, indicando a quantidade de bicicletas prontas para uso e o total de vagas livres em tempo real.
 RF-05 : O sistema deve exibir endereço, rota recomendada até o local e status operacional de cada estação selecionada.
 RF-06 (Validação de QR Code): O sistema deve capturar e validar o código QR escaneado, identificando a bicicleta correspondente e verificando se ela está apta para locação.
 RF-07 (Comando de Desbloqueio): O sistema deve emitir o comando de liberação para a trava inteligente e iniciar a contagem do tempo da corrida após a confirmação mecânica de abertura.
 RF-08 (Acompanhamento da Corrida): O sistema deve exibir ao ciclista a duração da corrida em andamento, estação de origem, bicicleta utilizada e custo estimado acumulado.
 RF-09 (Encerramento de Corrida): O sistema deve encerrar a locação mediante a detecção do travamento físico da bicicleta em uma estação autorizada e calcular o valor final da cobrança.
 RF-10 (Compra de Pacote de Minutos): O sistema deve permitir a compra de pacotes pré-pagos de minutos, creditando o saldo após a confirmação do pagamento.
 RF-11 (Processamento de Pagamento por PIX): O sistema deve gerar o QR Code dinâmico/código Copia e Cola do PIX e atualizar o status do pagamento em tempo real.
 RF-12 (Cobrança Automática no Cartão): O sistema deve processar a cobrança do valor final da corrida no cartão de crédito ou débito pré-autorizado assim que a viagem for concluída.
 RF-13 (Emissão de Comprovante de Viagem): O sistema deve gerar um extrato detalhado ao final de cada corrida com tempo total, trajeto (origem/destino), tarifa aplicada e método de pagamento utilizado.
 RF-14 (Reporte de Avarias pelo Ciclista): O sistema deve permitir que o ciclista relate problemas mecânicos (ex.: pneu murcho, freio avariado) durante o encerramento da corrida, alterando o status da bicicleta para ⁠Em Manutenção⁠.
 RF-15 (Bloqueio e Desbloqueio Manual): O sistema deve permitir que Administradores e Operadores alterem manualmente o status operacional de bicicletas e estações.
 RF-16 (Registro de Redistribuição de Frota): O sistema deve permitir ao Operador registrar a transferência em lote de bicicletas entre estações sobrecarregadas e desabastecidas.
 RF-17 (Painel de Métricas e Relatórios): O sistema deve fornecer ao Administrador relatórios de receita, taxa de ociosidade de bicicletas, índice de quebras e horários de pico por estação.

#Regras de negócio

Locação e Uso da Frota
RN-01 - Início da Corrida: O desbloqueio da bicicleta e o início da contagem de tempo da corrida só devem ocorrer mediante a validação e leitura bem-sucedida do QR Code da respectiva unidade pelo usuário.
RN-02 - Condição para Encerramento: Uma corrida só é considerada finalizada (pausando a cobrança) quando a bicicleta é travada fisicamente em uma estação de destino oficialmente autorizada pelo sistema.
RN-03 - Atualização de Disponibilidade: O mapa de estações deve refletir a disponibilidade de vagas vazias e de bicicletas prontas para uso em tempo real.
Tarifação e Pagamentos
RN-04 - Modelo de Cobrança: A tarifação do trajeto deve ser calculada de duas formas exclusivas: por minuto fracionado consumido ou mediante o débito de minutos de um pacote pré-pago ativo do usuário.
RN-05 - Procedimento de Atualização de Pagamento: Caso o pacote de minutos acabe durante uma corrida, os minutos excedentes serão debitados automáticamente no cartão cadastrado.
RN-06 - Condição de Uso/Aluguel: Para alugar uma bicicleta, o usuário deve possuir um cartão de crédito cadastrado. 
RN-07 - Métodos de Pagamento Aceitos: A liquidação financeira das corridas ou compra de pacotes deve ser realizada apenas via PIX, cartão de crédito ou cartão de débito.
RN-08 - Emissão de Comprovantes: Imediatamente após o travamento da bicicleta e cálculo do trajeto, o sistema deve emitir e disponibilizar um comprovante digital da transação ao ciclista.
Manutenção e Operação Logística
RN-09 - Bloqueio Preventivo Automático: Se o ciclista reportar um problema mecânico ao finalizar a corrida, o sistema deve alterar o status daquela bicicleta para "em manutenção", impedindo novos desbloqueios até a revisão.
RN-10 - Redistribuição de Frota: Apenas usuários com perfil de "Operador de Campo" têm autorização sistêmica para retirar bicicletas de uma estação e alocá-las em outra sem gerar cobrança, visando o balanceamento de vagas.
Gestão e Administração
RN-11 - Acesso Analítico: O acesso aos painéis de relatórios estratégicos (receita financeira, ociosidade de bicicletas e status de manutenção da frota) é restrito a usuários com privilégios de "Administrador".


#Histórias de Usuário

1º - Cadastrar
- Como um novo usuário, eu quero realizar o meu cadastro na plataforma informando e-mail, senha, CPF e dados de contato, de forma que eu possa criar minha conta e me autenticar para utilizar o serviço de bicicletas.

2º - Criar Estação
- Como um administrador, eu quero cadastrar uma nova estação informando nome, endereço, coordenadas geográficas (latitude e longitude) e a capacidade total de vagas, de forma que o local fique disponível no sistema para receber bicicletas e operações.

3º Vincular Método de Pagamento
- Como um ciclista autenticado, eu quero cadastrar os dados do meu cartão de crédito ou débito na minha conta, de forma que eu tenha uma forma de pagamento tokenizada e pronta para futuras cobranças de corridas.
