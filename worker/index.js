/* Trava de senha do Painel do Trader.
 *
 * Enquanto o site for só do dono, ele não pode ficar aberto na internet:
 * as licenças dos dados de mercado valem para uso pessoal, e um endereço
 * que qualquer um abre não é uso pessoal.
 *
 * Este arquivo roda ANTES de qualquer página ser entregue. Sem usuário e
 * senha certos, ninguém vê nada.
 *
 * A senha NÃO fica aqui. Ela fica nos segredos do Cloudflare, em
 * Settings > Variables and Secrets, nos nomes PAINEL_USUARIO e PAINEL_SENHA.
 * Por isso este repositório pode continuar público.
 *
 * Para tirar a trava um dia (site aberto ao público), basta apagar
 * "main" e "run_worker_first" do wrangler.jsonc.
 */

const AREA = 'Painel do Trader';

/* Compara dois textos sempre no mesmo tempo.
 * Uma comparação comum pararia no primeiro caractere diferente, e medir
 * esse tempo deixaria alguém adivinhar a senha letra por letra. */
function iguais(a, b) {
  const enc = new TextEncoder();
  const x = enc.encode(a);
  const y = enc.encode(b);
  // Tamanhos diferentes já bastam para negar, mas ainda assim percorremos
  // tudo para não entregar o tamanho da senha pelo tempo de resposta.
  let diferenca = x.length ^ y.length;
  const limite = Math.max(x.length, y.length);
  for (let i = 0; i < limite; i++) {
    diferenca |= (x[i] ?? 0) ^ (y[i] ?? 0);
  }
  return diferenca === 0;
}

function pedirSenha(mensagem) {
  return new Response(mensagem, {
    status: 401,
    headers: {
      'WWW-Authenticate': `Basic realm="${AREA}", charset="UTF-8"`,
      'Content-Type': 'text/plain; charset=utf-8',
      'Cache-Control': 'no-store',
    },
  });
}

function negar(mensagem) {
  return new Response(mensagem, {
    status: 503,
    headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' },
  });
}

export default {
  async fetch(request, env) {
    const usuario = env.PAINEL_USUARIO;
    const senha = env.PAINEL_SENHA;

    /* Se os segredos não estiverem cadastrados, o site fica FECHADO.
     * Falhar trancado, nunca destrancado: um erro de configuração não pode
     * acabar publicando os dados para a internet inteira. */
    if (!usuario || !senha) {
      return negar(
        'Painel ainda não configurado.\n\n' +
          'Cadastre os segredos PAINEL_USUARIO e PAINEL_SENHA no Cloudflare,\n' +
          'em Workers & Pages > painel-do-trader > Settings > Variables and Secrets.'
      );
    }

    const autorizacao = request.headers.get('Authorization') || '';
    if (!autorizacao.startsWith('Basic ')) {
      return pedirSenha('Este painel é privado. Informe usuário e senha.');
    }

    let informado;
    try {
      informado = atob(autorizacao.slice(6));
    } catch {
      return pedirSenha('Credenciais em formato inválido.');
    }

    /* O usuário não pode ter ":", mas a senha pode: só o primeiro separa. */
    const corte = informado.indexOf(':');
    if (corte < 0) {
      return pedirSenha('Credenciais em formato inválido.');
    }
    const usuarioInformado = informado.slice(0, corte);
    const senhaInformada = informado.slice(corte + 1);

    /* Os dois testes rodam sempre, sem "&&" curto-circuitando, para que o
     * tempo de resposta não revele se o usuário existe. */
    const usuarioOk = iguais(usuarioInformado, usuario);
    const senhaOk = iguais(senhaInformada, senha);
    if (!usuarioOk || !senhaOk) {
      return pedirSenha('Usuário ou senha incorretos.');
    }

    /* Passou. Entrega a página normalmente. */
    const resposta = await env.ASSETS.fetch(request);

    /* Conteúdo privado não deve ficar guardado em cache compartilhado
     * (o da Cloudflare, o do provedor, o de um proxy no meio do caminho). */
    const copia = new Response(resposta.body, resposta);
    copia.headers.set('Cache-Control', 'private, no-cache, must-revalidate');
    copia.headers.set('X-Robots-Tag', 'noindex, nofollow');
    return copia;
  },
};
