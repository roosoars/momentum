"""Service for sending emails."""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional


class EmailService:
    """Service for sending emails via SMTP."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: str = "Momentum",
    ):
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = smtp_username or os.getenv("SMTP_USERNAME", "")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD", "")
        self.from_email = from_email or os.getenv("SMTP_FROM_EMAIL", "")
        self.from_name = from_name
        self.enabled = bool(self.smtp_host and self.smtp_username and self.from_email)

    def send_verification_email(self, to_email: str, verification_token: str, base_url: str) -> bool:
        """
        Send email verification email.

        Args:
            to_email: Recipient email
            verification_token: Verification token
            base_url: Base URL for verification link

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            # Log verification URL for development
            verification_url = f"{base_url}/auth/verify-email?token={verification_token}"
            print(f"[EMAIL] Verification URL for {to_email}: {verification_url}")
            return True

        verification_url = f"{base_url}/auth/verify-email?token={verification_token}"

        subject = "Verifique seu email - Momentum"
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #0f172a; padding: 30px; border-radius: 10px; text-align: center;">
                    <h1 style="color: #93c5fd; margin: 0;">Momentum</h1>
                    <p style="color: #cbd5e1; margin-top: 10px;">Plataforma de Sinais</p>
                </div>

                <div style="padding: 30px 0;">
                    <h2 style="color: #1e293b; margin-bottom: 20px;">Bem-vindo ao Momentum!</h2>

                    <p style="color: #475569; line-height: 1.6; margin-bottom: 20px;">
                        Obrigado por se cadastrar. Para ativar sua conta e começar a receber sinais de trading,
                        por favor verifique seu endereço de email clicando no botão abaixo:
                    </p>

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{verification_url}"
                           style="background-color: #3b82f6; color: white; padding: 15px 30px;
                                  text-decoration: none; border-radius: 5px; display: inline-block;
                                  font-weight: bold;">
                            Verificar Email
                        </a>
                    </div>

                    <p style="color: #64748b; font-size: 14px; margin-top: 30px;">
                        Se você não criou uma conta no Momentum, pode ignorar este email.
                    </p>

                    <p style="color: #64748b; font-size: 14px; margin-top: 20px;">
                        Este link expira em 24 horas.
                    </p>
                </div>

                <div style="border-top: 1px solid #e2e8f0; padding-top: 20px; text-align: center;">
                    <p style="color: #94a3b8; font-size: 12px;">
                        © 2024 Momentum. Todos os direitos reservados.
                    </p>
                </div>
            </body>
        </html>
        """

        text_body = f"""
        Momentum - Verificação de Email

        Bem-vindo ao Momentum!

        Para ativar sua conta, acesse o link abaixo:
        {verification_url}

        Este link expira em 24 horas.

        Se você não criou uma conta no Momentum, pode ignorar este email.

        © 2024 Momentum
        """

        return self._send_email(to_email, subject, html_body, text_body)

    def _send_email(self, to_email: str, subject: str, html_body: str, text_body: str) -> bool:
        """
        Send an email via SMTP.

        Args:
            to_email: Recipient email
            subject: Email subject
            html_body: HTML body
            text_body: Plain text body

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email

            part1 = MIMEText(text_body, "plain", "utf-8")
            part2 = MIMEText(html_body, "html", "utf-8")

            msg.attach(part1)
            msg.attach(part2)

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            return True

        except Exception as e:
            print(f"[EMAIL ERROR] Failed to send email to {to_email}: {str(e)}")
            return False
