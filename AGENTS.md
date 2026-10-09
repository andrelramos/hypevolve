# Regras para agentes neste repositório

## Segurança de estado e corretude

- Use `icontract` para pré-condições, pós-condições e invariantes nas fronteiras
  que criam, transitam ou persistem o estado de uma execução.
- Um contrato deve expressar uma propriedade observável, sem efeitos colaterais;
  não duplique validação de tipos já coberta por anotações.
- Não introduza estados de sessão fora de `queued`, `running`, `completed` e
  `failed`. Uma execução concluída ou falha não pode voltar a `running`.
- Execute `make lint` antes de entregar alterações Python. Esse gate usa UV,
  roda `pyright` em modo estrito e `crosshair check hypevolve/contracts.py` para procurar
  violações dos contratos `icontract` por execução simbólica.
- Todo código novo ou modificado em `hypevolve/` deve ter tipagem completa;
  não use `Any`, `# type: ignore` ou cast para silenciar o Pyright sem uma
  justificativa local e verificável.

## Navegação de código

Se existir `.codegraph/` na raiz, use `codegraph explore` antes de grep/find
para localizar ou entender símbolos.
