import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from web3 import Web3

# Logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
AIRDROP_WALLET = os.getenv("AIRDROP_WALLET")
CONTRACT_ADDRESS = "0xd5baB4C1b92176f9690c0d2771EDbF18b73b8181"
CHANNEL_USERNAME = "@benjaminfranklintoken"
TOKEN_DECIMALS = 18
TOKEN_AMOUNT_MAIN = 500
TOKEN_AMOUNT_REFERRAL = 100

w3 = Web3(Web3.HTTPProvider("https://bsc-dataseed.binance.org/"))

# ABI
ERC20_ABI = [{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"}]

contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=ERC20_ABI)

users = {}
referrals = {}

def send_token(to_address, amount):
    try:
        nonce = w3.eth.get_transaction_count(AIRDROP_WALLET)
        tx = contract.functions.transfer(
            Web3.to_checksum_address(to_address),
            int(amount * 10**TOKEN_DECIMALS)
        ).build_transaction({
            'from': AIRDROP_WALLET,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': w3.to_wei('5', 'gwei')
        })
        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return tx_hash.hex()
    except Exception as e:
        logger.error(f"Token send error: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
    if member.status not in ["member", "creator", "administrator"]:
        await update.message.reply_text("❗️Please join our channel first:
" + CHANNEL_USERNAME)
        return

    if user_id not in users:
        users[user_id] = {"claimed": False}

    if args:
        try:
            referrer_id = int(args[0])
            if referrer_id != user_id and "ref_by" not in users[user_id]:
                users[user_id]["ref_by"] = referrer_id
                referrals.setdefault(referrer_id, []).append(user_id)
        except:
            pass

    invite_link = f"https://t.me/{context.bot.username}?start={user_id}"
    await update.message.reply_text(
        "👋 Welcome!

"
        "💸 Send your BSC wallet address to receive **500 BJF**.
"
        "👥 Invite friends to earn **100 BJF** per invite:
"
        f"{invite_link}"
    )

async def handle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet = update.message.text.strip()

    if not Web3.is_address(wallet):
        await update.message.reply_text("❌ Invalid wallet address.")
        return

    if users.get(user_id, {}).get("claimed"):
        await update.message.reply_text("✅ Airdrop already claimed.")
        return

    tx = send_token(wallet, TOKEN_AMOUNT_MAIN)
    if tx:
        users[user_id]["wallet"] = wallet
        users[user_id]["claimed"] = True
        await update.message.reply_text(f"🎉 500 BJF sent! TX: {tx}")

        referrer_id = users[user_id].get("ref_by")
        if referrer_id and users.get(referrer_id, {}).get("wallet"):
            tx2 = send_token(users[referrer_id]["wallet"], TOKEN_AMOUNT_REFERRAL)
            if tx2:
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=f"🎁 You earned 100 BJF for referring {user_id}! TX: {tx2}"
                )
    else:
        await update.message.reply_text("⚠️ Failed to send tokens.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet))
    app.run_polling()

if __name__ == "__main__":
    main()
