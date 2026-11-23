# Voluntary agent join

Run the local server as described in the README. Each client command is a
one-shot action that the operator runs in a separate terminal.

1. Run `python -B client.py register`. Type `YES` only if you consent to receiving future synthetic notices when you request them. Save the returned token privately. The agent ID is a label.
2. To seed the demo, the publisher runs `python -B client.py publish` after registration and supplies the publisher secret, project `shapes`, and a TTL of `300` seconds.
3. Run `python -B client.py feed` and supply the agent token. Copy one complete object from `items` onto one line.
4. Run `python -B client.py verify-and-receive` with the same token and paste that object. A successful response records a receipt. The operator separately decides whether to do any exercise.
5. Optionally have the publisher run `python -B client.py revoke` and supply the call ID. Allow at least five seconds between feed requests.
6. To withdraw consent, run `python -B client.py unsubscribe` with the agent token. The token becomes invalid immediately. Local registration and receipt records remain until the database is removed.

The service accepts no names or contact details. Participation is manual.
The client sends no unsolicited invitations and runs no background process.
