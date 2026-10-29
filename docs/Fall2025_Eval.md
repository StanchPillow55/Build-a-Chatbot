<table>
<tbody>
<tr>
<td><p><strong>Item</strong></p></td>
<td><p>Finding</p></td>
</tr>
<tr>
<td><p>Question</p></td>
<td><p>What days are the Project Pitches?</p></td>
</tr>
<tr>
<td><p>Expected answer</p></td>
<td><p>September 10 and September 17, 2025</p></td>
</tr>
<tr>
<td><p>Supporting source</p></td>
<td><p>Project Timeline.docx</p></td>
</tr>
<tr>
<td><p>Original setting</p></td>
<td><p><code>top_k=4</code></p></td>
</tr>
<tr>
<td><p>Original result</p></td>
<td><p>Refused; timeline ranked seventh and wasn’t retrieved</p></td>
</tr>
<tr>
<td><p>Change tested</p></td>
<td><p>Increased <code>top_k</code> to 8</p></td>
</tr>
<tr>
<td><p>New result</p></td>
<td><p>Correct dates, but cited the PDF’s agenda instead of the
timeline</p></td>
</tr>
<tr>
<td><p>Remaining issue</p></td>
<td><p>Citation selection</p></td>
</tr>
<tr>
<td><p>Proposed next experiment</p></td>
<td><p>Strengthen citation instructions in the prompt — <strong>not yet
verified</strong></p></td>
</tr>
</tbody>
</table>
