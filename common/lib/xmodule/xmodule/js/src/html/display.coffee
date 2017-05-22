class @HTMLModule

  constructor: (@element) ->
    @el = $(@element)
    JavascriptLoader.executeModuleScripts(@el)
    Collapsible.setCollapsibles(@el)
    if MathJax? and MathJax.Hub?
	    MathJax.Hub.Queue ["Typeset", MathJax.Hub, @el[0]]
    if setupFullScreenModal?
      setupFullScreenModal()

  $: (selector) ->
    $(selector, @el)
