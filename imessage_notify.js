import { IMessageSDK } from '@photon-ai/imessage-kit'

async function main() {
    // skip node and script path
    const [, , phoneArg, ...rest] = process.argv
    const phone = process.env.IMESSAGE_PHONE || phoneArg
    const text = rest.join(' ') || process.env.IMESSAGE_MESSAGE

    if (!phone || !text) {
        console.error('Missing phone number or message')
        process.exit(1)
    }

    const sdk = new IMessageSDK()
    
    try {
        await sdk.send(phone, text)
        console.log('Message sent successfully')
    } catch (error) {
        console.error('iMessage send error:', error)
        process.exitCode = 1
    } finally {
        // give it a moment to flush if needed, though sdk.send should be awaited
        // sdk.close() if the SDK has a close method, based on snippet it does
        if (sdk.close) await sdk.close()
    }
}

main().catch(error => {
    console.error('iMessage notify script error:', error)
    process.exit(1)
})
