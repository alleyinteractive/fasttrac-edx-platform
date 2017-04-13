var edx = edx || {},

    Navigation = (function() {

        var navigation = {

            init: function() {
                if ($('.accordion').length) {
                    navigation.loadAccordion();
                }
            },

            loadAccordion: function() {
                navigation.checkForCurrent();
                navigation.listenForClick();
                navigation.listenForKeypress();
            },

            getActiveSection: function() {
                return $('.accordion .hidden-button-chapter.active');
            },

            sendActiveIndexToDropdown: function(id) {
                var $item = $('#' + id);
                // update dropdown display value
                $('.accordion .dropbtn-value span.active-section').text($item.find('.display-name').text());
                // remove any other active class
                $item.addClass('active');
            },

            checkForCurrent: function() {
                var activeSection = navigation.getActiveSection();
                var sectionId = activeSection.attr('data-id');

                var $subsections = $('.accordion').find('#' + activeSection.attr('data-controls'));

                navigation.removeCurrentlyActiveItem();
                navigation.sendActiveIndexToDropdown(sectionId);

                if ($subsections !== null) {
                    navigation.openAccordion($subsections)
                }
            },

            listenForClick: function() {
                $('.accordion').on('click', '.button-chapter', function(event) {
                    event.preventDefault();

                    var section = $('#' + $(this).attr('data-child-id'));

                    navigation.closeAccordions();
                    navigation.openAccordion(section);
                });
            },

            removeCurrentlyActiveItem: function() {
                $('.accordion .chapter-item').each(function() {
                    $(this).removeClass('active');
                })
            },

            listenForKeypress: function() {
                $('.accordion').on('keydown', '.button-chapter', function(event) {
                    // because we're changing the role of the toggle from an 'a' to a 'button'
                    // we need to ensure it has the same keyboard use cases as a real button.
                    // this is useful for screenreader users primarily.
                    if (event.which == 32) { // spacebar
                        event.preventDefault();
                        $(event.currentTarget).trigger('click');
                    } else {
                        return true;
                    }
                });
            },

            closeAccordions: function() {
                $('.accordion .chapter-content-container').each(function() {
                    $(this).find('.chapter-menu')
                        .removeClass('is-open')
                        .removeAttr('style'); //remove inline style from slideDown()
                });
            },

            openAccordion: function(section) {
                var $sectionEl = $(section);

                $sectionEl.find('.chapter-menu')
                    .addClass('is-open')
                    .slideDown();
            }
        };

        return {
            init: navigation.init
        };

    })();

    edx.util = edx.util || {};
    edx.util.navigation = Navigation;
    edx.util.navigation.init();
