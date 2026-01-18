#!/usr/bin/env node

import { IMessageSDK } from '@photon-ai/imessage-kit'

async function main() {
  const [, , phoneArg, ...rest] = process.argv
  const phone = process.env.IMESSAGE_PHONE || phoneArg
  const text = rest.join(' ') || process.env.IMESSAGE_MESSAGE

  if (!phone || !text) {
    console.error('Missing phone number or message for iMessage notification')
    process.exit(1)
  }

  const sdk = new IMessageSDK()

  try {
    await sdk.send(phone, text)
  } catch (error) {
    console.error('iMessage send error', error)
    process.exitCode = 1
  } finally {
    await sdk.close()
  }
}

main().catch(error => {
  console.error('iMessage notify script error', error)
  process.exit(1)
})

