<template>
  <div class="datacolumn">

<h3>Data Position List</h3>
<div class="timestamp">{{last_rcvd}}</div>

<ul id="example-1" class="scrolling" >
  <li class="datalist" v-for="item in datablocks" :key="item.acid">
    acid:{{ item.acid }}
    <br/>
    type:{{ item.actype }}
  </li>
</ul>

  </div>
</template>

<script>

export default {
    data () {
      return {
        last_rcvd: new Date(),

        datablocks : [
          { acid: 'N111', actype: 'C172' },
          { acid: 'N112', actype: 'C172' },
          { acid: 'N113', actype: 'C172' },
          { acid: 'N114', actype: 'C172' },
          { acid: 'N115', actype: 'C172' },
          { acid: 'N116', actype: 'C172' },
          { acid: 'N117', actype: 'C172' },
          { acid: 'N118', actype: 'C172' },
          { acid: 'N118', actype: 'C172' },
          { acid: 'N120', actype: 'C172' },
          { acid: 'N121', actype: 'C172' },
          { acid: 'N122', actype: 'C172' },
          { acid: 'N123', actype: 'C172' },
          { acid: 'N124', actype: 'C172' },
          { acid: 'N125', actype: 'C172' },
          { acid: 'N126', actype: 'C172' },
          { acid: 'N127', actype: 'C172' },
          { acid: 'N129', actype: 'C172' },
          { acid: 'N130', actype: 'C172' } ]
      }
    },

  mounted () {

      this.$root.$on('dlist', (dlist) => {
      console.log("DataPos received dlist");
      this.datablocks = dlist;
    })
  }
}

</script>

<style lang="scss">
/* https://www.w3schools.com/css/default.asp */

div.datacolumn {
    background-color: #ffecb3;
}

div.timestamp {
  font-size: 70%;
}

li.datalist {
    border-style: solid;
    border-color: black;
    background-color: #e6ffcc;

    margin-top: 5px;
    margin-bottom: 5px;
}

ul.scrolling {
        max-height: 400px;
        overflow: scroll;
}

</style>

