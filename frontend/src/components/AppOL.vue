<template>
  <div style="background-color: orange">

    <!-- ========== map & view ========= -->
    <vl-map  :load-tiles-while-animating="true"
             :load-tiles-while-interacting="true"
             data-projection="EPSG:4326"
             ref="map"
              @mounted="onMapMounted"
           >

    <vl-view ref="view"
             :zoom.sync="zoom"
             :center.sync="center"
             :rotation.sync="rotation"></vl-view>

      <!-- ========== layers ========= -->
      <vl-layer-tile id="osm">
        <vl-source-osm></vl-source-osm>
      </vl-layer-tile>

      <!-- flight path features layer -->
      <vl-layer-vector >
        <vl-source-vector :url="geojsonUrl"
                          :features.sync="features" />
      </vl-layer-vector>

      <!-- kml features layer -->
      <vl-layer-vector >
          <vl-source-vector :url="kmlUrl"
                            :format-factory="kmlFormatFactory" />
      </vl-layer-vector>

      <!-- asdex layer -->
      <vl-layer-vector >
        <vl-source-vector :url="asdexUrl"
                          :features.sync="features" />
        <vl-style-func :factory="asdexStyleFuncFac" />
      </vl-layer-vector>

      <!-- ========== end ========= -->
    </vl-map>

  </div>
</template>

<script>

// $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

import ZoomSlider from 'ol/control/ZoomSlider'
import ScaleLine  from 'ol/control/ScaleLine'
import Stroke     from 'ol/style/Stroke'
import Style      from 'ol/style/Style'
import KML        from 'ol/format/KML'

// ==========================================================

const methods = {

    onMapMounted () {
      // now ol.Map instance is ready and we can work with it directly
      this.$refs.map.$map.getControls().extend([
        new ScaleLine(),
        new ZoomSlider(),
      ])
    },

    kmlFormatFactory () {
      //return new ol.format.KML()
      return new KML()
    },

    // attempt to color lines
    asdexStyleFuncFac() {
      const activestyle = new Style({
          stroke: new Stroke({
            color: 'magenta',
            width: 3.25,
          })
      })

      return (feature) => {
        // help: using feature is pointless;
        // but what is an 'arrow function' with no args???
        if (feature.get('acid')) {
          return activestyle
        }
        return activestyle
     }
  }
}

// ==========================================================

var KSTL = [-90.3700289, 38.7486972];

export default {
    methods,
    data () {
      return {
        zoom: 5,
        center: KSTL,
        rotation: 0,

        geojsonUrl: '',
        features: [],

        kmlUrl: '',

        asdexUrl: '',
        asdexFeats: [],

      }
    },

// ==========================================================

  mounted () {

    // -------------------------
    this.$root.$on('geojsonurl', (the_query) => {
      console.log("geojson:"+the_query);

      this.geojsonUrl = the_query;   // << that's all we have to do!
    })
    // -------------------------
    this.$root.$on('kmlurl', (the_query) => {
      console.log("kml:"+the_query);

      this.kmlUrl = the_query;
    })
    // -------------------------
    this.$root.$on('asdexurl', (the_query) => {
      console.log("asdex::"+the_query);

      this.asdexUrl = the_query;
    })
    // -------------------------
  },

// ==========================================================
}

</script>

