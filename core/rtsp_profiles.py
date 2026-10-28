"""
Fábrica de URLs RTSP e Motor de Diagnóstico / Fallback de Rotas.
Gera rotas canônicas e alternativas para contornar variações de firmware
em Hikvision, HiLook, Intelbras, Dahua e ONVIF.
"""

import re
import socket
import urllib.parse
from typing import List, Optional, Tuple

import cv2
from core.models import Brand, Camera, StreamType


class RTSPProfileFactory:
    """Gera e testa URLs RTSP com múltiplos caminhos de fallback por fabricante."""

    @staticmethod
    def _encode_auth(user: str, password: str) -> str:
        """Codifica credenciais de forma segura preservando caracteres aceitos."""
        safe_user = urllib.parse.quote(user, safe="")
        safe_pass = urllib.parse.quote(password, safe="")
        return f"{safe_user}:{safe_pass}"

    @classmethod
    def get_candidate_urls(cls, camera: Camera, stream_type: StreamType) -> List[str]:
        """
        Retorna uma lista ordenada de URLs candidatas baseadas na marca e canal.
        Se o substream não estiver habilitado na câmera, inclui o main stream como fallback.
        """
        auth = cls._encode_auth(camera.username, camera.password)
        raw_auth = f"{camera.username}:{camera.password}"
        host = f"{camera.ip}:{camera.port}"
        ch = camera.channel

        candidates = []

        if camera.brand in (Brand.HIKVISION, Brand.HILOOK):
            suffix = "01" if stream_type == StreamType.MAIN else "02"
            stream_id = f"{ch}{suffix}"

            # 1. Padrão canônico moderno Hikvision (/Streaming/Channels/101 ou 102)
            candidates.append(f"rtsp://{auth}@{host}/Streaming/Channels/{stream_id}")
            # 2. Rota curta (/Streaming/Channels/1 ou /Streaming/Channels/2)
            alt_id = f"{ch}" if stream_type == StreamType.MAIN else f"{ch * 2}"
            candidates.append(f"rtsp://{auth}@{host}/Streaming/Channels/{alt_id}")
            # 3. Se substream falhar, tentar canal 1 direto (muitas câmeras só têm stream 1)
            if stream_type == StreamType.SUB:
                candidates.append(f"rtsp://{auth}@{host}/Streaming/Channels/{ch}01")
                candidates.append(f"rtsp://{auth}@{host}/Streaming/Channels/{ch}")
            # 4. Padrão legacy H.264
            st_str = "main" if stream_type == StreamType.MAIN else "sub"
            candidates.append(f"rtsp://{auth}@{host}/h264/ch{ch}/{st_str}/av_stream")
            # 5. Padrão ISAPI
            candidates.append(f"rtsp://{auth}@{host}/ISAPI/Streaming/channels/{stream_id}")
            # 6. Rota /live/ch
            candidates.append(f"rtsp://{auth}@{host}/live/ch{ch}")

        elif camera.brand in (Brand.INTELBRAS, Brand.DAHUA):
            subtype = 0 if stream_type == StreamType.MAIN else 1
            # 1. Padrão Oficial Intelbras / Dahua (/cam/realmonitor)
            candidates.append(f"rtsp://{auth}@{host}/cam/realmonitor?channel={ch}&subtype={subtype}")
            if stream_type == StreamType.SUB:
                # Fallback para main stream caso substream esteja desativado
                candidates.append(f"rtsp://{auth}@{host}/cam/realmonitor?channel={ch}&subtype=0")
            # 2. Padrão Intelbras Mibo / Wi-Fi
            candidates.append(f"rtsp://{auth}@{host}/live/ch{ch}")
            # 3. Rota ONVIF padrão
            candidates.append(f"rtsp://{auth}@{host}/onvif{ch}")
            candidates.append(f"rtsp://{auth}@{host}/Streaming/Channels/{ch}01")

        elif camera.brand == Brand.HOLOWITS:
            # Holowits / Huawei Intelligent Vision (Rotas Oficiais e ONVIF Media)
            media_id = "Media1" if stream_type == StreamType.MAIN else "Media2"
            candidates.append(f"rtsp://{auth}@{host}/LiveMedia/ch{ch}/{media_id}")
            if stream_type == StreamType.SUB:
                candidates.append(f"rtsp://{auth}@{host}/LiveMedia/ch{ch}/Media1")
            candidates.append(f"rtsp://{auth}@{host}/LiveMedia/ch{ch}/Media0")
            candidates.append(f"rtsp://{auth}@{host}/live/ch{ch}")
            candidates.append(f"rtsp://{auth}@{host}/live/ch0")
            candidates.append(f"rtsp://{auth}@{host}/video1" if stream_type == StreamType.MAIN else f"rtsp://{auth}@{host}/video2")
            candidates.append(f"rtsp://{auth}@{host}/media/video1" if stream_type == StreamType.MAIN else f"rtsp://{auth}@{host}/media/video2")
            candidates.append(f"rtsp://{auth}@{host}/Streaming/Channels/{ch}0{1 if stream_type == StreamType.MAIN else 2}")
            candidates.append(f"rtsp://{auth}@{host}/Streaming/Channels/{ch}")
            candidates.append(f"rtsp://{auth}@{host}/onvif/live/media{1 if stream_type == StreamType.MAIN else 2}")

        elif camera.brand == Brand.POSITIVO:
            # Positivo Casa Inteligente / Segurança
            st_idx = "0" if stream_type == StreamType.MAIN else "1"
            candidates.append(f"rtsp://{auth}@{host}/live/ch{st_idx}")
            candidates.append(f"rtsp://{auth}@{host}/live/ch{ch}")
            candidates.append(f"rtsp://{auth}@{host}/onvif{1 if stream_type == StreamType.MAIN else 2}")
            candidates.append(f"rtsp://{auth}@{host}/media/stream1")
            candidates.append(f"rtsp://{auth}@{host}/Streaming/Channels/101")

        elif camera.brand == Brand.UNIVIEW:
            # Uniview (UNV) Padrão Oficial
            s_idx = "0" if stream_type == StreamType.MAIN else "1"
            candidates.append(f"rtsp://{auth}@{host}/unicast/c{ch}/s{s_idx}/live")
            if stream_type == StreamType.SUB:
                candidates.append(f"rtsp://{auth}@{host}/unicast/c{ch}/s0/live")
            candidates.append(f"rtsp://{auth}@{host}/media/video{1 if stream_type == StreamType.MAIN else 2}")
            candidates.append(f"rtsp://{auth}@{host}/Streaming/Channels/{ch}0{1 if stream_type == StreamType.MAIN else 2}")
            candidates.append(f"rtsp://{auth}@{host}/live/ch{ch}")

        else:
            # Genérico / ONVIF RTSP
            candidates.append(f"rtsp://{auth}@{host}/live/ch{ch}")
            candidates.append(f"rtsp://{auth}@{host}/onvif{ch}")
            candidates.append(f"rtsp://{auth}@{host}/Streaming/Channels/{ch}01")
            candidates.append(f"rtsp://{auth}@{host}/cam/realmonitor?channel={ch}&subtype=0")

        # Se houver senha com caracteres especiais que possam ter sido alterados pelo percent-encode,
        # adiciona também versão com credenciais diretas
        if raw_auth != auth:
            for url in list(candidates):
                raw_url = url.replace(auth, raw_auth)
                if raw_url not in candidates:
                    candidates.append(raw_url)

        return candidates

    @classmethod
    def build_url(cls, camera: Camera, stream_type: StreamType) -> str:
        """Retorna a URL prioritária canônica."""
        candidates = cls.get_candidate_urls(camera, stream_type)
        return candidates[0] if candidates else f"rtsp://{camera.ip}:{camera.port}"

    @classmethod
    def probe_and_diagnose(cls, camera: Camera) -> Tuple[bool, Optional[str], Optional[str], str]:
        """
        Diagnostica a conexão física e descobre a rota RTSP exata suportada pelo dispositivo.
        Retorna: (sucesso, working_main_url, working_sub_url, mensagem_diagnostica)
        """
        # 1. Teste de conectividade física na porta RTSP
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.5)
        try:
            res = sock.connect_ex((camera.ip, camera.port))
            if res != 0:
                return (
                    False,
                    None,
                    None,
                    f"Porta {camera.port} inacessível em {camera.ip}. Câmera desligada ou subrede diferente."
                )
        except Exception as e:
            return False, None, None, f"Erro de conexão com host {camera.ip}: {e}"
        finally:
            sock.close()

        # 2. Testa as URLs candidatas
        sub_candidates = cls.get_candidate_urls(camera, StreamType.SUB)
        main_candidates = cls.get_candidate_urls(camera, StreamType.MAIN)

        working_sub_url = None
        working_main_url = None
        detected_res = ""

        for i, url in enumerate(sub_candidates):
            cap = None
            try:
                cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        h, w = frame.shape[:2]
                        detected_res = f"{w}x{h} px"
                        working_sub_url = url
                        working_main_url = main_candidates[min(i, len(main_candidates) - 1)]
                        break
            except Exception:
                pass
            finally:
                if cap is not None:
                    cap.release()

        if working_sub_url:
            masked = cls.mask_credentials(working_sub_url)
            return (
                True,
                working_main_url,
                working_sub_url,
                f"Conectado com sucesso! Resolução: {detected_res} | Rota: {masked}"
            )

        # 3. Diagnóstico de credencial
        if not camera.password:
            return (
                False,
                None,
                None,
                "A porta 554 respondeu, mas a câmera exige senha. Clique em 'Editar Câmera' e preencha a senha correta."
            )

        return (
            False,
            None,
            None,
            f"Porta {camera.port} respondeu, mas o fluxo foi recusado pela câmera. Causas frequentes:\n"
            "1. Senha ou usuário incorretos (câmeras Hikvision exigem senha configurada na ativação);\n"
            "2. O protocolo ONVIF/RTSP precisa ser ativado na página web da câmera;\n"
            "3. O canal selecionado está desativado no dispositivo."
        )

    @staticmethod
    def mask_credentials(rtsp_url: str) -> str:
        """Oculta a senha da URL RTSP para exibição segura."""
        return re.sub(r":([^@]+)@", r":****@", rtsp_url)
